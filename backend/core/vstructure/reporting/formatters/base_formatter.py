# reporting/formatters/base_formatter.py
"""
Formateador base para reportes.
"""

from abc import ABC, abstractmethod
from typing import Any, List
from ..models import ValidationReport


class BaseFormatter(ABC):
    """Interfaz base para formateadores de reportes."""
    
    @abstractmethod
    def format(self, report: ValidationReport) -> Any:
        """
        Formatea un reporte al formato específico.
        
        Args:
            report: Reporte a formatear
            
        Returns:
            Datos formateados (depende de la implementación)
        """
        pass
    
    @property
    @abstractmethod
    def format_name(self) -> str:
        """Nombre del formato."""
        pass
    
    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Extensión de archivo para este formato."""
        pass