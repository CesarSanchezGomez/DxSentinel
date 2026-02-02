# reporting/formatters/json_formatter.py
"""
Formateador JSON para reportes.
"""

import json
from datetime import datetime
from typing import Any, Dict, List
from .base_formatter import BaseFormatter
from ..models import ValidationReport


class JSONFormatter(BaseFormatter):
    """Formatea reportes a JSON."""
    
    def format(self, report: ValidationReport) -> str:
        """
        Formatea reporte a JSON.
        
        Args:
            report: Reporte a formatear
            
        Returns:
            JSON string
        """
        # Convertir reporte a diccionario
        report_dict = report.to_dict()
        
        # Formatear con indentación para legibilidad
        return json.dumps(
            report_dict,
            indent=2,
            ensure_ascii=False,
            default=self._json_serializer
        )
    
    def _json_serializer(self, obj: Any) -> Any:
        """Serializador personalizado para objetos no serializables por defecto."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Tipo {type(obj)} no serializable")
    
    @property
    def format_name(self) -> str:
        return "json"
    
    @property
    def file_extension(self) -> str:
        return ".json"