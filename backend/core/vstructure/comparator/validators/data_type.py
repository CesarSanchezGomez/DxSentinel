# comparator/validators/data_type.py - CORREGIDO
"""
Regla: Validación de tipo de dato.
"""

from typing import List, Optional
import re
from datetime import datetime
from .base_rule import BaseRule
from ..models import ValidationContext, ValidationScope, ValidationError, FieldMetadata
from ..errors import ComparatorErrors


class DataTypeRule(BaseRule):
    """Valida que los valores coincidan con el tipo de dato especificado en metadata."""
    
    # Patrones de validación por tipo
    TYPE_PATTERNS = {
        "string": None,  # Todo es string por defecto
        "number": r'^-?\d+(\.\d+)?$',
        "integer": r'^-?\d+$',
        "boolean": r'^(true|false|0|1|yes|no)$',
        "date": r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
        "datetime": r'^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',
        "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    }
    
    def __init__(self):
        super().__init__(
            rule_id="data_type",
            description="Valida tipo de dato según metadata"
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
        if not field_metadata or not field_metadata.data_type:
            return errors  # No hay tipo especificado
        
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return errors  # Valores vacíos no se validan (ya cubierto por not_null)
        
        if entity_id is None or row_index is None or csv_row_index is None:
            return errors
        
        data_type = field_metadata.data_type.lower()
        value_str = str(value).strip()
        
        # Validar según tipo
        is_valid = self._validate_type(data_type, value_str)
        
        if not is_valid:
            errors.append(
                ComparatorErrors.invalid_data_type(
                    row_index=row_index,
                    csv_row_index=csv_row_index,
                    entity_id=entity_id,
                    field_id=field_metadata.field_id,
                    column_name=column_name or f"{entity_id}_{field_metadata.field_id}",
                    expected_type=data_type,
                    actual_value=value_str[:50],  # Truncar para mensaje
                    person_id_external=person_id_external  # <-- PASA EL IDENTIFICADOR
                )
            )
        
        return errors
    
    def _validate_type(self, data_type: str, value: str) -> bool:
        """Valida un valor contra un tipo de dato."""
        
        if data_type not in self.TYPE_PATTERNS:
            # Tipo desconocido, asumir string
            return True
        
        pattern = self.TYPE_PATTERNS.get(data_type)
        
        if pattern is None:  # string
            return True
        
        # Validar con regex
        if not re.match(pattern, value, re.IGNORECASE):
            return False
        
        # Validaciones adicionales específicas
        if data_type == "date":
            try:
                datetime.strptime(value, "%Y-%m-%d")
                return True
            except ValueError:
                return False
        
        elif data_type == "boolean":
            # Normalizar valores booleanos
            normalized = value.lower()
            return normalized in ["true", "false", "0", "1", "yes", "no"]
        
        return True
    
    def should_skip(self, field_metadata=None, value=None) -> bool:
        # Saltar si no hay tipo especificado
        if not field_metadata or not field_metadata.data_type:
            return True
        # Saltar valores vacíos
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return True
        return False