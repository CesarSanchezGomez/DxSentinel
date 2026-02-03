"""
Formateador CSV para reportes.
ACTUALIZADO: Columnas en español, sin timestamp/row_index.
"""

import csv
import io
from typing import Any, List
from .base_formatter import BaseFormatter
from ..models import ValidationReport, ReportEntry


class CSVFormatter(BaseFormatter):
    """Formatea reportes a CSV."""
    
    def format(self, report: ValidationReport) -> str:
        """
        Formatea reporte a CSV.
        
        Args:
            report: Reporte a formatear
            
        Returns:
            CSV string
        """
        # Crear buffer en memoria
        output = io.StringIO()
        
        # Configurar writer CSV
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        # Escribir header en español
        header = [
            "identificador",
            "campo_id",
            "columna",
            "codigo_error",
            "nivel",
            "mensaje",
            "valor_esperado",
            "valor_actual",
            "ruta_metadata"
        ]
        writer.writerow(header)
        
        # Escribir cada entrada
        for entry in report.entries:
            row = [
                entry.identificador or "",
                entry.field_id or "",
                entry.column_name or "",
                entry.error_code,
                entry.level.value,
                entry.message,
                str(entry.expected) if entry.expected is not None else "",
                str(entry.actual) if entry.actual is not None else "",
                entry.metadata_path or ""
            ]
            writer.writerow(row)
        
        return output.getvalue()
    
    @property
    def format_name(self) -> str:
        return "csv"
    
    @property
    def file_extension(self) -> str:
        return ".csv"