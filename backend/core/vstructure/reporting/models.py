# reporting/models.py
"""
Modelos de datos para reporting.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ReportFormat(Enum):
    JSON = "json"
    CSV = "csv"
    SUMMARY = "summary"


class ReportLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ReportEntry:
    """Entrada individual en el reporte."""
    timestamp: datetime
    row_index: Optional[int]
    csv_row_index: Optional[int]
    entity_id: Optional[str]
    field_id: Optional[str]
    column_name: Optional[str]
    error_code: str
    message: str
    level: ReportLevel
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    metadata_path: Optional[str] = None
    details: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "row_index": self.row_index,
            "csv_row_index": self.csv_row_index,
            "entity_id": self.entity_id,
            "field_id": self.field_id,
            "column_name": self.column_name,
            "error_code": self.error_code,
            "message": self.message,
            "level": self.level.value,
            "expected": self.expected,
            "actual": self.actual,
            "metadata_path": self.metadata_path,
            "details": self.details
        }


@dataclass
class ValidationMetrics:
    """Métricas de validación."""
    total_rows: int = 0
    total_batches: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    validation_time: float = 0.0
    
    # Conteo por tipo de error
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    # Conteo por entidad
    entity_error_counts: Dict[str, int] = field(default_factory=dict)
    
    # Conteo por severidad
    severity_counts: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "total_rows": self.total_rows,
            "total_batches": self.total_batches,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "validation_time": self.validation_time,
            "error_counts": self.error_counts,
            "entity_error_counts": self.entity_error_counts,
            "severity_counts": self.severity_counts
        }


@dataclass
class ValidationReport:
    """Reporte completo de validación."""
    report_id: str
    timestamp: datetime
    source_csv: str
    source_metadata: str
    entries: List[ReportEntry] = field(default_factory=list)
    metrics: ValidationMetrics = field(default_factory=ValidationMetrics)
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte reporte completo a diccionario."""
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "source_csv": self.source_csv,
            "source_metadata": self.source_metadata,
            "summary": self.summary,
            "entries": [entry.to_dict() for entry in self.entries],
            "metrics": self.metrics.to_dict()
        }