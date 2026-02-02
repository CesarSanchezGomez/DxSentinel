# reporting/errors.py
"""
Errores del módulo reporting.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReportingError:
    """Error en la generación de reportes."""
    code: str
    message: str
    details: Optional[dict] = None


class ReportingErrors:
    """Factory de errores de reporting."""
    
    @staticmethod
    def export_failed(format: str, details: str = "") -> ReportingError:
        return ReportingError(
            code="EXPORT_FAILED",
            message=f"Fallo al exportar reporte en formato {format}",
            details={"format": format, "reason": details}
        )
    
    @staticmethod
    def file_write_failed(filepath: str, details: str = "") -> ReportingError:
        return ReportingError(
            code="FILE_WRITE_FAILED",
            message=f"Fallo al escribir archivo: {filepath}",
            details={"filepath": filepath, "reason": details}
        )
    
    @staticmethod
    def invalid_format(format: str) -> ReportingError:
        return ReportingError(
            code="INVALID_FORMAT",
            message=f"Formato de reporte no soportado: {format}",
            details={"format": format}
        )