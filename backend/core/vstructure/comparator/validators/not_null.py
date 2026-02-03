# comparator/validators/not_null.py - CORREGIDO
"""
Regla: Campos requeridos no deben ser nulos/vacíos.
"""

from typing import List, Optional
from .base_rule import BaseRule
from ..models import ValidationContext, ValidationScope, ValidationError, FieldMetadata
from ..errors import ComparatorErrors


class NotNullRule(BaseRule):
    """Valida que campos requeridos no sean nulos o vacíos."""
    
    def __init__(self):
        super().__init__(
            rule_id="not_null",
            description="Valida que campos requeridos no sean nulos/vacíos"
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
        if not field_metadata or not field_metadata.is_required:
            return errors  # Solo validar campos requeridos
        
        if entity_id is None or row_index is None or csv_row_index is None:
            return errors  # Necesario para errores específicos
        
        # Validar si el valor es nulo o vacío
        is_null_or_empty = (
            value is None or 
            (isinstance(value, str) and value.strip() == "")
        )
        
        if is_null_or_empty:
            errors.append(
                ComparatorErrors.required_value_missing(
                    row_index=row_index,
                    csv_row_index=csv_row_index,
                    entity_id=entity_id,
                    field_id=field_metadata.field_id,
                    column_name=column_name or f"{entity_id}_{field_metadata.field_id}",
                    person_id_external=person_id_external  # <-- PASA EL IDENTIFICADOR
                )
            )
        
        return errors
    
    def should_skip(self, field_metadata=None, value=None) -> bool:
        # Saltar si no es campo requerido
        if field_metadata and not field_metadata.is_required:
            return True
        return False