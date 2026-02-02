# comparator/orchestrator.py
"""
Punto de entrada principal del comparator.
"""

from typing import Dict, Tuple, Optional, List
import time

from realtime import Any
from .models import ValidationContext, BatchValidationResult, ValidationError
from .rule_registry import RuleRegistry
from .rule_engine import RuleEngine
from .context_adapter import MetadataAdapter
from .errors import ComparatorErrors


class ComparisonOrchestrator:
    """Orquestador principal del comparator."""
    
    def __init__(self):
        self.rule_registry = RuleRegistry()
        self.rule_engine = RuleEngine(self.rule_registry)
    
    def create_validation_context(
        self,
        transform_context: Any,
        metadata_instance_id: str = None,
        metadata_version: Optional[str] = None,
        parsed_metadata: Dict[str, Any] = None
    ) -> Tuple[Optional[ValidationContext], Optional[str]]:
        """
        Crea contexto de validación combinando transform y metadata.
        
        Args:
            transform_context: Contexto del transformer
            metadata_instance_id: ID de instancia metadata (opcional si parsed_metadata se proporciona)
            metadata_version: Versión de metadata (opcional)
            parsed_metadata: Metadata ya parseada (alternativa a cargarla)
            
        Returns:
            Tupla (ValidationContext, mensaje_error)
        """
        try:
            # 1. Cargar/adaptar metadata
            if parsed_metadata is not None:
                print(f"📥 Adaptando metadata parseada proporcionada...")
                metadata_context = MetadataAdapter.adapt_parsed_metadata(
                    parsed_metadata=parsed_metadata
                )
            elif metadata_instance_id is not None:
                # Cargar desde instancia
                print(f"📥 Cargando metadata: {metadata_instance_id} v{metadata_version or 'latest'}")
                metadata_context = MetadataAdapter.load_and_adapt_metadata(
                    instance_id=metadata_instance_id,
                    version=metadata_version
                )
            else:
                return None, "Se requiere metadata_instance_id o parsed_metadata"
            
            # Verificar si hubo error
            if hasattr(metadata_context, 'stats') and metadata_context.stats.get("error"):
                return None, f"Error con metadata: {metadata_context.stats['error']}"
            
            print(f"   ✓ Metadata cargada: {len(metadata_context.entities)} entidades, "
                f"{len(metadata_context.field_by_full_path)} campos")
            
            # 2. Crear contexto de validación
            validation_context = ValidationContext(
                transform_context=transform_context,
                metadata_context=metadata_context
            )
            
            # 3. Configurar estadísticas iniciales
            validation_context.validation_stats = {
                "start_time": time.time(),
                "metadata_source": f"{metadata_context.source_instance}_{metadata_context.source_version}",
                "csv_columns": len(transform_context.parsed_columns),
                "csv_entities": len(transform_context.entities),
                "metadata_entities": len(metadata_context.entities),
                "metadata_fields": len(metadata_context.field_by_full_path)
            }
            
            return validation_context, None
            
        except Exception as e:
            return None, f"Error creando contexto de validación: {str(e)}"
    def validate_csv(
        self,
        validation_context: ValidationContext
    ) -> Tuple[List[BatchValidationResult], List[ValidationError]]:
        """
        Ejecuta validación completa del CSV.
        
        Args:
            validation_context: Contexto de validación
            
        Returns:
            Tupla (resultados por lote, errores globales)
        """
        global_errors = []
        batch_results = []
        
        try:
            print(f"\n🔍 Iniciando validación...")
            print(f"   Reglas habilitadas: {', '.join(validation_context.enabled_rules)}")
            
            # Obtener stream de datos del CSV
            data_stream = validation_context.transform_context.csv_context.data_stream
            
            # Ejecutar validación por lotes
            batch_results = self.rule_engine.validate_all_batches(
                data_stream=data_stream,
                context=validation_context,
                transform_orchestrator=None  # TODO: Pasar referencia real
            )
            
            # Procesar resultados
            total_rows = 0
            total_errors = 0
            total_time = 0
            
            for batch_result in batch_results:
                total_rows += batch_result.processed_rows
                total_errors += len(batch_result.errors)
                total_time += batch_result.validation_time
            
            # Actualizar estadísticas
            validation_context.validation_stats.update({
                "end_time": time.time(),
                "total_rows": total_rows,
                "total_batches": len(batch_results),
                "total_errors": total_errors,
                "total_validation_time": total_time,
                "avg_time_per_row": total_time / total_rows if total_rows > 0 else 0,
                "avg_time_per_batch": total_time / len(batch_results) if batch_results else 0
            })
            
            print(f"\n📊 Validación completada:")
            print(f"   Filas procesadas: {total_rows}")
            print(f"   Lotes procesados: {len(batch_results)}")
            print(f"   Errores encontrados: {total_errors}")
            print(f"   Tiempo total: {total_time:.2f}s")
            
        except Exception as e:
            global_errors.append(
                ComparatorErrors.rule_execution_failed(
                    "global_validation",
                    f"Error en validación global: {str(e)}"
                )
            )
        
        # Añadir errores globales al contexto
        validation_context.errors.extend(global_errors)
        
        return batch_results, global_errors
    
    def get_validation_summary(
        self,
        validation_context: ValidationContext,
        batch_results: List[BatchValidationResult]
    ) -> Dict:
        """
        Genera resumen de validación.
        
        Args:
            validation_context: Contexto de validación
            batch_results: Resultados por lote
            
        Returns:
            Diccionario con resumen
        """
        # Contar errores por tipo
        error_counts = {}
        for batch_result in batch_results:
            for error in batch_result.errors:
                error_counts[error.code] = error_counts.get(error.code, 0) + 1
        
        # Contar errores por entidad
        entity_error_counts = {}
        for batch_result in batch_results:
            for error in batch_result.errors:
                if error.entity_id:
                    entity_error_counts[error.entity_id] = entity_error_counts.get(error.entity_id, 0) + 1
        
        # Calcular tiempos
        total_validation_time = sum(b.result.validation_time for b in batch_results)
        
        return {
            "metadata_source": validation_context.validation_stats.get("metadata_source"),
            "csv_columns": validation_context.validation_stats.get("csv_columns"),
            "total_rows": validation_context.validation_stats.get("total_rows", 0),
            "total_batches": len(batch_results),
            "total_errors": sum(len(b.errors) for b in batch_results),
            "error_counts": error_counts,
            "entity_error_counts": entity_error_counts,
            "validation_time": total_validation_time,
            "rules_executed": validation_context.enabled_rules,
            "has_errors": any(len(b.errors) > 0 for b in batch_results)
        }