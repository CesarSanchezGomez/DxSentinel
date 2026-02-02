# src/vstructure/reporting/__init__.py
"""
Módulo de reporting para validación estructural.
"""

from .orchestrator import ReportingOrchestrator
from .models import (
    ValidationReport, ReportEntry, ValidationMetrics,
    ReportFormat, ReportLevel
)
from .errors import ReportingErrors
from .aggregator import ReportAggregator

# Importar formatters desde sus módulos
from .formatters.json_formatter import JSONFormatter
from .formatters.csv_formatter import CSVFormatter

# Importar exporters
from .exporters.file_exporter import FileExporter

__all__ = [
    'ReportingOrchestrator',
    'ValidationReport',
    'ReportEntry',
    'ValidationMetrics',
    'ReportFormat',
    'ReportLevel',
    'ReportingErrors',
    'ReportAggregator',
    'JSONFormatter',
    'CSVFormatter',
    'FileExporter'
]