# csv_loader/errors.py
"""
Errores normalizados del csv_loader.
"""

from .models import ErrorSeverity, NormalizedError


class CsvLoaderErrors:
    """Factory de errores normalizados."""
    
    @staticmethod
    def empty_file() -> NormalizedError:
        return NormalizedError(
            code="EMPTY_FILE",
            severity=ErrorSeverity.FATAL,
            message="Archivo CSV vacío o sin contenido"
        )
    
    @staticmethod
    def missing_header_row() -> NormalizedError:
        return NormalizedError(
            code="MISSING_HEADER_ROW",
            severity=ErrorSeverity.FATAL,
            message="No se encontró la fila de identificadores técnicos (fila 1)"
        )
    
    @staticmethod
    def empty_column_name(row_index: int, col_index: int) -> NormalizedError:
        return NormalizedError(
            code="EMPTY_COLUMN_NAME",
            severity=ErrorSeverity.FATAL,
            message="Nombre de columna vacío en header",
            row_index=row_index,
            column_index=col_index
        )
    
    @staticmethod
    def duplicated_column(row_index: int, col_index: int, column_name: str) -> NormalizedError:
        return NormalizedError(
            code="DUPLICATED_COLUMN",
            severity=ErrorSeverity.FATAL,
            message=f"Nombre de columna duplicado: '{column_name}'",
            row_index=row_index,
            column_index=col_index,
            value=column_name
        )
    
    @staticmethod
    def invalid_column_identifier(row_index: int, col_index: int, column_name: str) -> NormalizedError:
        return NormalizedError(
            code="INVALID_COLUMN_IDENTIFIER",
            severity=ErrorSeverity.FATAL,
            message=f"Identificador de columna no válido: '{column_name}'",
            row_index=row_index,
            column_index=col_index,
            value=column_name
        )
    
    @staticmethod
    def missing_label_row() -> NormalizedError:
        return NormalizedError(
            code="MISSING_LABEL_ROW",
            severity=ErrorSeverity.ERROR,
            message="No se encontró la fila de etiquetas (fila 2)"
        )
    
    @staticmethod
    def label_column_mismatch(row_index: int, expected: int, actual: int) -> NormalizedError:
        return NormalizedError(
            code="LABEL_COLUMN_MISMATCH",
            severity=ErrorSeverity.ERROR,
            message=f"Fila de etiquetas tiene {actual} columnas, se esperaban {expected}",
            row_index=row_index
        )
    
    @staticmethod
    def no_data_rows() -> NormalizedError:
        return NormalizedError(
            code="NO_DATA_ROWS",
            severity=ErrorSeverity.WARNING,
            message="Golden Record sin datos (solo header y labels)"
        )
    
    @staticmethod
    def row_column_mismatch(row_index: int, expected: int, actual: int) -> NormalizedError:
        return NormalizedError(
            code="ROW_COLUMN_COUNT_MISMATCH",
            severity=ErrorSeverity.ERROR,
            message=f"Fila tiene {actual} columnas, se esperaban {expected}",
            row_index=row_index
        )
    
    @staticmethod
    def malformed_row(row_index: int, details: str = "") -> NormalizedError:
        return NormalizedError(
            code="MALFORMED_ROW",
            severity=ErrorSeverity.ERROR,
            message=f"Fila mal formada: {details}",
            row_index=row_index
        )
    
    @staticmethod
    def encoding_detection_failed() -> NormalizedError:
        return NormalizedError(
            code="ENCODING_DETECTION_FAILED",
            severity=ErrorSeverity.FATAL,
            message="No se pudo detectar la codificación del archivo"
        )
    
    @staticmethod
    def invalid_characters(row_index: int, col_index: int) -> NormalizedError:
        return NormalizedError(
            code="INVALID_CHARACTERS",
            severity=ErrorSeverity.ERROR,
            message="Caracteres inválidos en la codificación detectada",
            row_index=row_index,
            column_index=col_index
        )
    
    @staticmethod
    def csv_dialect_detection_failed() -> NormalizedError:
        return NormalizedError(
            code="CSV_DIALECT_DETECTION_FAILED",
            severity=ErrorSeverity.FATAL,
            message="No se pudo detectar el dialecto CSV"
        )
    
    @staticmethod
    def unsupported_csv_dialect(dialect: str) -> NormalizedError:
        return NormalizedError(
            code="UNSUPPORTED_CSV_DIALECT",
            severity=ErrorSeverity.FATAL,
            message=f"Dialecto CSV no soportado: {dialect}"
        )