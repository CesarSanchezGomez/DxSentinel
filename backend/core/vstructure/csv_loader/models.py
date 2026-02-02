# csv_loader/models.py
"""
Modelos de datos internos del csv_loader.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Iterator
from enum import Enum


class ErrorSeverity(Enum):
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass
class NormalizedError:
    """Error normalizado para reporte."""
    code: str
    severity: ErrorSeverity
    message: str
    row_index: Optional[int] = None
    column_index: Optional[int] = None
    value: Optional[str] = None


@dataclass
class CsvDialectInfo:
    """Información detectada del dialecto CSV."""
    delimiter: str = ","
    quotechar: str = '"'
    escapechar: Optional[str] = None
    doublequote: bool = True
    skipinitialspace: bool = False
    lineterminator: str = "\n"
    quoting: int = 0  # csv.QUOTE_MINIMAL


@dataclass
class CsvContext:
    """Contexto de CSV detectado."""
    encoding: str
    dialect: CsvDialectInfo
    columns: List[str] = field(default_factory=list)
    total_columns: int = 0
    errors: List[NormalizedError] = field(default_factory=list)
    raw_data: List[List[str]] = field(default_factory=list)  # Datos completos
    data_stream: Optional[Iterator[List[List[str]]]] = None
    label_row_present: bool = False
    data_start_index: int = 2  # <-- AÑADIR ESTE ATRIBUTO (1 = solo header, 2 = header+labels)
    
    @property
    def has_labels(self) -> bool:
        """Indica si el CSV tiene fila de etiquetas."""
        return self.label_row_present