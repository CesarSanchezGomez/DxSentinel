# comparator/validators/required_column.py - CORREGIDO
"""
Regla: Columnas requeridas deben existir en CSV.
"""

from typing import List, Optional
from .base_rule import BaseRule
from ..models import FieldMetadata, ValidationContext, ValidationScope, ValidationError
from ..errors import ComparatorErrors


class RequiredColumnRule(BaseRule):
    """Valida que todas las columnas requeridas en metadata existan en CSV."""
    
    def __init__(self):
        super().__init__(
            rule_id="required_columns",
            description="Valida existencia de columnas requeridas"
        )
    
    @property
    def scope(self):
        return ValidationScope.ENTITY
    
    def validate(
        self, 
        context: ValidationContext,
        entity_id: Optional[str] = None,
        field_metadata: Optional["FieldMetadata"] = None,
        value: Optional[str] = None,
        row_index: Optional[int] = None,
        csv_row_index: Optional[int] = None,
        column_name: Optional[str] = None,
        person_id_external: Optional[str] = None  # <-- NUEVO PARÁMETRO (aunque no se usa en esta regla)
    ) -> List[ValidationError]:
        errors = []
        
        # Para cada entidad en metadata
        for meta_entity_id, meta_entity in context.metadata_context.entities.items():
            # Buscar entidad correspondiente en transform context
            transform_entity = context.transform_context.entities.get(meta_entity_id)
            
            if not transform_entity:
                # Entidad no encontrada en CSV - error solo si tiene campos requeridos
                required_fields = meta_entity.required_fields
                if required_fields:
                    for field_id in required_fields:
                        errors.append(
                            ComparatorErrors.required_column_missing(meta_entity_id, field_id)
                            # No tiene person_id_external porque es error a nivel columna, no fila
                        )
                continue
            
            # Para cada campo requerido en metadata
            for field_id in meta_entity.required_fields:
                # Verificar si existe en CSV
                field_exists = any(
                    col.field_id == field_id for col in transform_entity.columns
                )
                
                if not field_exists:
                    errors.append(
                        ComparatorErrors.required_column_missing(meta_entity_id, field_id)
                        # No tiene person_id_external porque es error a nivel columna, no fila
                    )
        
        return errors
    
    def should_skip(self, field_metadata=None, value=None) -> bool:
        # Esta regla siempre se ejecuta a nivel entidad
        return False