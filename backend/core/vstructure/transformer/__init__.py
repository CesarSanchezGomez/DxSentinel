# transformer/__init__.py
"""
Micromódulo para transformación de datos CSV a estructura semántica.
"""

from .orchestrator import TransformationOrchestrator
from .models import (
    TransformationContext,
    TransformedRow,
    ParsedColumn,
    EntityData,
    TransformationError,
    TransformationSeverity,
    BatchTransformationResult
)
from .errors import TransformerErrors

__all__ = [
    'TransformationOrchestrator',
    'TransformationContext',
    'TransformedRow',
    'ParsedColumn',
    'EntityData',
    'TransformationError',
    'TransformationSeverity',
    'BatchTransformationResult',
    'TransformerErrors'
]