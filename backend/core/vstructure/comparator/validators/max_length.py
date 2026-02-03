# comparator/validators/max_length.py - CORREGIDO
"""
Regla: Validación de longitud máxima.
"""

from typing import List, Optional
from .base_rule import BaseRule
from ..models import ValidationContext, ValidationScope, ValidationError, FieldMetadata
from ..errors import ComparatorErrors


class MaxLengthRule(BaseRule):
    """Valida que los valores no excedan la longitud máxima especificada."""
    
    def __init__(self):
        super().__init__(
            rule_id="max_length",
            description="Valida longitud máxima según metadata"
        )
    
    @property
    def scope(self):
        return ValidationScope.FIELD
    
    def validate(
        self, 
        context: ValidationContext,
        entity_id: Optional[str] = None,
        field_metadata: Optional[FieldMetadata] = None,
        value: Optional[str] = None,
        row_index: Optional[int] = None,
        csv_row_index: Optional[int] = None,
        column_name: Optional[str] = None,
        person_id_external: Optional[str] = None  # <-- NUEVO PARÁMETRO
    ) -> List[ValidationError]:
        errors = []
        
        # Validar precondiciones
        if not field_metadata or field_metadata.max_length is None:
            return errors  # No hay longitud máxima especificada
        
        if value is None:
            return errors  # Valores nulos no tienen longitud
        
        if entity_id is None or row_index is None or csv_row_index is None:
            return errors
        
        # Calcular longitud
        value_str = str(value)
        actual_length = len(value_str)
        max_length = field_metadata.max_length
        
        # Validar longitud
        if actual_length > max_length:
            errors.append(
                ComparatorErrors.max_length_exceeded(
                    row_index=row_index,
                    csv_row_index=csv_row_index,
                    entity_id=entity_id,
                    field_id=field_metadata.field_id,
                    column_name=column_name or f"{entity_id}_{field_metadata.field_id}",
                    max_length=max_length,
                    actual_length=actual_length,
                    value=value_str,
                    person_id_external=person_id_external  # <-- PASA EL IDENTIFICADOR
                )
            )
        
        return errors
    
    def should_skip(self, field_metadata=None, value=None) -> bool:
        # Saltar si no hay longitud máxima especificada
        if not field_metadata or field_metadata.max_length is None:
            return True
        # Saltar valores nulos
        if value is None:
            return True
        return False