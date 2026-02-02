# transformer/errors.py
"""
Errores normalizados del transformer.
"""

from realtime import List
from .models import TransformationSeverity, TransformationError


class TransformerErrors:
    """Factory de errores del transformer."""
    
    @staticmethod
    def invalid_column_composition(column_name: str, details: str = "") -> TransformationError:
        return TransformationError(
            code="INVALID_COLUMN_COMPOSITION",
            severity=TransformationSeverity.ERROR,
            message=f"Identificador de columna no válido: '{column_name}'",
            column_name=column_name,
            details={"reason": details}
        )
    
    @staticmethod
    def unknown_entity_structure(column_name: str) -> TransformationError:
        return TransformationError(
            code="UNKNOWN_ENTITY_STRUCTURE",
            severity=TransformationSeverity.WARNING,
            message=f"No se pudo identificar estructura de entidad en columna: '{column_name}'",
            column_name=column_name
        )
    
    @staticmethod
    def transformation_failed(row_index: int, details: str = "") -> TransformationError:
        return TransformationError(
            code="TRANSFORMATION_FAILED",
            severity=TransformationSeverity.FATAL,
            message=f"Fallo en transformación de fila {row_index}: {details}",
            row_index=row_index
        )
    
    @staticmethod
    def entity_parsing_error(column_name: str, parsed_parts: List[str]) -> TransformationError:
        return TransformationError(
            code="ENTITY_PARSING_ERROR",
            severity=TransformationSeverity.WARNING,
            message=f"Partes insuficientes en identificador de columna: '{column_name}'",
            column_name=column_name,
            details={"parsed_parts": parsed_parts}
        )
    
    @staticmethod
    def missing_country_code(column_name: str) -> TransformationError:
        return TransformationError(
            code="MISSING_COUNTRY_CODE",
            severity=TransformationSeverity.ERROR,
            message=f"Columna específica de país sin código: '{column_name}'",
            column_name=column_name
        )
    
    @staticmethod
    def ambiguous_entity_mapping(column_name: str, possible_entities: List[str]) -> TransformationError:
        return TransformationError(
            code="AMBIGUOUS_ENTITY_MAPPING",
            severity=TransformationSeverity.WARNING,
            message=f"Mapeo ambiguo para columna '{column_name}'",
            column_name=column_name,
            details={"possible_entities": possible_entities}
        )
    
    @staticmethod
    def row_transformation_error(row_index: int, col_index: int, error_msg: str) -> TransformationError:
        return TransformationError(
            code="ROW_TRANSFORMATION_ERROR",
            severity=TransformationSeverity.ERROR,
            message=f"Error transformando fila {row_index}, columna {col_index}: {error_msg}",
            row_index=row_index,
            column_name=f"col_{col_index}"
        )