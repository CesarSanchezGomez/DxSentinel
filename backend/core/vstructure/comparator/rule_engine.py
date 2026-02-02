# comparator/rule_engine.py
"""
Motor de ejecución de reglas.
"""

import time
from typing import List, Dict, Any, Iterator

from realtime import Optional
from .models import (
    ValidationContext, ValidationError, BatchValidationResult,
    ValidationScope, FieldMetadata
)
from .rule_registry import RuleRegistry
from .errors import ComparatorErrors


class RuleEngine:
    """Motor principal de ejecución de reglas de validación."""
    
    def __init__(self, rule_registry: RuleRegistry):
        self.rule_registry = rule_registry
        self._global_rules = []
        self._entity_rules = []
        self._field_rules = []
        
        self._categorize_rules()
    
    def _categorize_rules(self):
        """Categoriza reglas por scope para ejecución eficiente."""
        self._global_rules = self.rule_registry.get_enabled_rules(ValidationScope.GLOBAL.value)
        self._entity_rules = self.rule_registry.get_enabled_rules(ValidationScope.ENTITY.value)
        self._field_rules = self.rule_registry.get_enabled_rules(ValidationScope.FIELD.value)
    
    def validate_batch(
        self,
        batch_rows: List[Dict],  # Lista de TransformedRow
        batch_index: int,
        context: ValidationContext
    ) -> BatchValidationResult:
        """
        Valida un lote de filas transformadas.
        
        Args:
            batch_rows: Lista de filas transformadas
            batch_index: Índice del lote
            context: Contexto de validación
            
        Returns:
            Resultado de validación del lote
        """
        start_time = time.time()
        all_errors: List[ValidationError] = []
        
        try:
            # 1. Ejecutar reglas globales (una vez por lote)
            global_errors = self._execute_global_rules(context)
            all_errors.extend(global_errors)
            
            # 2. Ejecutar reglas por entidad (una vez por lote)
            entity_errors = self._execute_entity_rules(context)
            all_errors.extend(entity_errors)
            
            # 3. Ejecutar reglas por fila/campo
            for row in batch_rows:
                row_errors = self._validate_row(row, context)
                all_errors.extend(row_errors)
            
        except Exception as e:
            # Capturar error fatal en la ejecución
            all_errors.append(
                ComparatorErrors.rule_execution_failed(
                    f"batch_{batch_index}",
                    str(e)
                )
            )
        
        validation_time = time.time() - start_time
        
        return BatchValidationResult(
            batch_index=batch_index,
            processed_rows=len(batch_rows),
            errors=all_errors,
            validation_time=validation_time
        )
    
    def _execute_global_rules(self, context: ValidationContext) -> List[ValidationError]:
        """Ejecuta reglas de scope GLOBAL."""
        errors = []
        
        for rule in self._global_rules:
            try:
                rule_errors = rule.validate(context)
                errors.extend(rule_errors)
            except Exception as e:
                errors.append(
                    ComparatorErrors.rule_execution_failed(
                        rule.rule_id,
                        str(e)
                    )
                )
        
        return errors
    
    def _execute_entity_rules(self, context: ValidationContext) -> List[ValidationError]:
        """Ejecuta reglas de scope ENTITY."""
        errors = []
        
        for rule in self._entity_rules:
            try:
                rule_errors = rule.validate(context)
                errors.extend(rule_errors)
            except Exception as e:
                errors.append(
                    ComparatorErrors.rule_execution_failed(
                        rule.rule_id,
                        str(e)
                    )
                )
        
        return errors
    
    def _validate_row(self, row: Dict, context: ValidationContext) -> List[ValidationError]:
        """
        Valida una fila individual.
        
        Args:
            row: TransformedRow
            context: Contexto de validación
            
        Returns:
            Lista de errores para la fila
        """
        errors = []
        
        # Para cada entidad en la fila
        for entity_id, entity_data in row.data_by_entity.items():
            # Para cada campo en la entidad
            for field_id, value in entity_data.items():
                # Obtener metadata del campo
                full_path = f"{entity_id}_{field_id}"
                field_metadata = context.metadata_context.field_by_full_path.get(full_path)
                
                # Si no hay metadata, buscar por field_id dentro de la entidad
                if not field_metadata and entity_id in context.metadata_context.entities:
                    entity_metadata = context.metadata_context.entities[entity_id]
                    field_metadata = entity_metadata.fields.get(field_id)
                
                # Ejecutar reglas por campo
                field_errors = self._validate_field(
                    entity_id=entity_id,
                    field_metadata=field_metadata,
                    value=value,
                    row_index=row.original_row_index,
                    csv_row_index=row.csv_row_index,
                    column_name=None,  # TODO: Obtener nombre real de columna
                    context=context
                )
                
                errors.extend(field_errors)
        
        return errors
    
    def _validate_field(
        self,
        entity_id: str,
        field_metadata: Optional[FieldMetadata],
        value: Any,
        row_index: int,
        csv_row_index: int,
        column_name: Optional[str],
        context: ValidationContext
    ) -> List[ValidationError]:
        """Ejecuta todas las reglas de campo para un campo específico."""
        errors = []
        
        # **CAMBIOS: Obtener field_id de manera más robusta**
        field_id = None
        
        if field_metadata and hasattr(field_metadata, 'field_id'):
            field_id = field_metadata.field_id
        else:
            # Intentar extraer de diferentes fuentes
            if column_name:
                # El column_name viene del CSV (ej: MEX_homeAddress_fiscal_street)
                # Necesitamos extraer solo el field_id (última parte)
                parts = column_name.split('_')
                if len(parts) >= 2:
                    field_id = parts[-1]
                else:
                    field_id = column_name
            else:
                field_id = 'unknown_field'
        
        # **CAMBIOS: Buscar metadata usando múltiples patrones**
        if not field_metadata:
            # **NUEVO: Estrategia de búsqueda múltiple para campos CSF**
            search_patterns = self._build_field_search_patterns(entity_id, field_id, column_name)
            
            # Buscar en todos los patrones
            for pattern in search_patterns:
                if pattern in context.metadata_context.field_by_full_path:
                    field_metadata = context.metadata_context.field_by_full_path[pattern]
                    break
            
            # Si aún no se encuentra, buscar en la entidad específica
            if not field_metadata and entity_id in context.metadata_context.entities:
                entity_metadata = context.metadata_context.entities[entity_id]
                field_metadata = entity_metadata.fields.get(field_id)
        
        # **CAMBIOS: Si no hay metadata para este campo, warning específico**
        if not field_metadata:
            # Intentar determinar el tipo de campo para mensaje más específico
            is_csf_field = entity_id.startswith(("MEX_", "USA_", "BRA_", "CAN_"))
            field_path = f"{entity_id}_{field_id}"
            
            if is_csf_field:
                errors.append(
                    ComparatorErrors.missing_metadata_for_field(
                        f"CSF Field: {field_path} (not found with country prefix)"
                    )
                )
            else:
                errors.append(
                    ComparatorErrors.missing_metadata_for_field(field_path)
                )
            return errors
        
        # **CAMBIOS RESTANTES: Continuar con validación normal...**
        # Ejecutar cada regla de campo
        for rule in self._field_rules:
            try:
                # Verificar si la regla debe saltarse
                if rule.should_skip(field_metadata, value):
                    continue
                
                # Ejecutar validación
                rule_errors = rule.validate(
                    context=context,
                    entity_id=entity_id,
                    field_metadata=field_metadata,
                    value=value,
                    row_index=row_index,
                    csv_row_index=csv_row_index,
                    column_name=column_name
                )
                
                errors.extend(rule_errors)
                
            except Exception as e:
                errors.append(
                    ComparatorErrors.rule_execution_failed(
                        rule.rule_id,
                        f"field {entity_id}.{field_id}: {str(e)}"
                    )
                )
        
        return errors
    
    def _build_field_search_patterns(self, entity_id: str, field_id: str, column_name: Optional[str]) -> List[str]:
        """
        Construye múltiples patrones de búsqueda para un campo.
        """
        patterns = []
        
        # **PATRÓN 1: Entity_Field (element_id ya es correcto, sin prefijo país)**
        patterns.append(f"{entity_id}_{field_id}")
        
        # **PATRÓN 2: Si entity_id parece tener prefijo país, intentar sin él**
        if entity_id.startswith(("MEX_", "USA_", "BRA_", "CAN_")):
            # El ColumnParser ya NO debería dar entity_ids con prefijo país
            # Pero por si acaso, intentar sin prefijo
            parts = entity_id.split('_', 1)
            if len(parts) == 2:
                base_entity = parts[1]
                patterns.append(f"{base_entity}_{field_id}")
        
        # **PATRÓN 3: Buscar directamente por column_name**
        if column_name:
            patterns.append(column_name)
            
            # **PATRÓN 4: Column_name con diferentes separadores**
            patterns.append(column_name.replace('_', '.'))
        
        # **PATRÓN 5: Para campos CSF, buscar con prefijo país**
        # (Ya se añadió en context_adapter)
        if column_name and column_name.startswith(("MEX_", "USA_", "BRA_")):
            patterns.append(column_name)  # Ya está en patrón 3, pero para claridad
        
        # Eliminar duplicados y vacíos
        unique_patterns = []
        for pattern in patterns:
            if pattern and pattern not in unique_patterns:
                unique_patterns.append(pattern)
        
        return unique_patterns
    
    def validate_all_batches(
        self,
        data_stream: Iterator[List[Dict]],  # Iterator de batches de TransformedRow
        context: ValidationContext,
        transform_orchestrator: Any  # Para transformar batches
    ) -> List[BatchValidationResult]:
        """
        Valida todos los lotes del stream de datos.
        
        Args:
            data_stream: Stream de batches CSV crudos
            context: Contexto de validación
            transform_orchestrator: Orquestador del transformer
            
        Returns:
            Lista de resultados por lote
        """
        batch_results = []
        batch_index = 0
        
        for raw_batch in data_stream:
            # Transformar batch crudo a estructura transformada
            batch_transform_result = transform_orchestrator._transform_batch(
                raw_batch, batch_index, context.transform_context
            )
            
            # Validar batch transformado
            batch_result = self.validate_batch(
                batch_rows=batch_transform_result.transformed_rows,
                batch_index=batch_index,
                context=context
            )
            
            batch_results.append(batch_result)
            batch_index += 1
        
        return batch_results