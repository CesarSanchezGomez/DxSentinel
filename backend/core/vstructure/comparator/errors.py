# comparator/errors.py
"""
Errores normalizados del comparator.
"""

from .models import ValidationError, ValidationSeverity, ValidationScope


class ComparatorErrors:
    """Factory de errores del comparator."""
    
    # Errores de adaptación de metadata
    @staticmethod
    def metadata_adaptation_failed(details: str = "") -> ValidationError:
        return ValidationError(
            code="METADATA_ADAPTATION_FAILED",
            severity=ValidationSeverity.FATAL,
            message=f"Fallo en adaptación de metadata: {details}",
            scope=ValidationScope.GLOBAL
        )
    
    @staticmethod
    def missing_metadata_for_field(field_path: str) -> ValidationError:
        return ValidationError(
            code="MISSING_METADATA_FOR_FIELD",
            severity=ValidationSeverity.WARNING,
            message=f"No se encontró metadata para campo: {field_path}",
            scope=ValidationScope.GLOBAL,
            metadata_path=field_path
        )
    
    @staticmethod
    def metadata_field_mismatch(expected: str, actual: str) -> ValidationError:
        return ValidationError(
            code="METADATA_FIELD_MISMATCH",
            severity=ValidationSeverity.WARNING,
            message=f"Mismatch entre metadata y datos: esperado '{expected}', actual '{actual}'",
            scope=ValidationScope.GLOBAL
        )
    
    # Errores de reglas
    @staticmethod
    def required_column_missing(entity_id: str, field_id: str) -> ValidationError:
        return ValidationError(
            code="REQUIRED_COLUMN_MISSING",
            severity=ValidationSeverity.ERROR,
            message=f"Columna requerida faltante: {entity_id}.{field_id}",
            scope=ValidationScope.ENTITY,
            entity_id=entity_id,
            field_id=field_id
        )
    
    @staticmethod
    def required_value_missing(
        row_index: int, csv_row_index: int, 
        entity_id: str, field_id: str, column_name: str
    ) -> ValidationError:
        return ValidationError(
            code="REQUIRED_VALUE_MISSING",
            severity=ValidationSeverity.ERROR,
            message=f"Valor requerido faltante en {entity_id}.{field_id}",
            scope=ValidationScope.ROW,
            row_index=row_index,
            csv_row_index=csv_row_index,
            entity_id=entity_id,
            field_id=field_id,
            column_name=column_name
        )
    
    @staticmethod
    def invalid_data_type(
        row_index: int, csv_row_index: int,
        entity_id: str, field_id: str, column_name: str,
        expected_type: str, actual_value: str
    ) -> ValidationError:
        return ValidationError(
            code="INVALID_DATA_TYPE",
            severity=ValidationSeverity.ERROR,
            message=f"Tipo de dato inválido en {entity_id}.{field_id}: esperado {expected_type}",
            scope=ValidationScope.FIELD,
            row_index=row_index,
            csv_row_index=csv_row_index,
            entity_id=entity_id,
            field_id=field_id,
            column_name=column_name,
            expected=expected_type,
            actual=actual_value
        )
    
    @staticmethod
    def max_length_exceeded(
        row_index: int, csv_row_index: int,
        entity_id: str, field_id: str, column_name: str,
        max_length: int, actual_length: int, value: str
    ) -> ValidationError:
        return ValidationError(
            code="MAX_LENGTH_EXCEEDED",
            severity=ValidationSeverity.ERROR,
            message=f"Longitud máxima excedida en {entity_id}.{field_id}: máximo {max_length}, actual {actual_length}",
            scope=ValidationScope.FIELD,
            row_index=row_index,
            csv_row_index=csv_row_index,
            entity_id=entity_id,
            field_id=field_id,
            column_name=column_name,
            expected=max_length,
            actual=actual_length,
            details={"truncated_value": value[:50] + "..." if len(value) > 50 else value}
        )
    
    @staticmethod
    def rule_execution_failed(rule_id: str, details: str = "") -> ValidationError:
        return ValidationError(
            code="RULE_EXECUTION_FAILED",
            severity=ValidationSeverity.FATAL,
            message=f"Fallo en ejecución de regla '{rule_id}': {details}",
            scope=ValidationScope.GLOBAL,
            details={"rule_id": rule_id}
        )