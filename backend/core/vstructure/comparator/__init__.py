# comparator/__init__.py
"""
Micromódulo para comparación y validación estructural.
"""

from .orchestrator import ComparisonOrchestrator
from .models import (
    ValidationContext,
    ValidationError,
    ValidationSeverity,
    ValidationScope,
    MetadataContext,
    FieldMetadata,
    EntityMetadata,
    BatchValidationResult,
    RuleConfiguration
)
from .errors import ComparatorErrors
from .validators import ALL_RULES, BaseRule
from .context_adapter import MetadataAdapter
from .rule_registry import RuleRegistry
from .rule_engine import RuleEngine

__all__ = [
    'ComparisonOrchestrator',
    'ValidationContext',
    'ValidationError',
    'ValidationSeverity',
    'ValidationScope',
    'MetadataContext',
    'FieldMetadata',
    'EntityMetadata',
    'BatchValidationResult',
    'RuleConfiguration',
    'ComparatorErrors',
    'ALL_RULES',
    'BaseRule',
    'MetadataAdapter',
    'RuleRegistry',
    'RuleEngine'
]