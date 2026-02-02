# comparator/validators/__init__.py
"""
Exporta todas las reglas de validación.
"""

from .base_rule import BaseRule
from .required_column import RequiredColumnRule
from .not_null import NotNullRule
from .data_type import DataTypeRule
from .max_length import MaxLengthRule

# Lista de todas las reglas disponibles
ALL_RULES = {
    "required_columns": RequiredColumnRule,
    "not_null": NotNullRule,
    "data_type": DataTypeRule,
    "max_length": MaxLengthRule
}

__all__ = [
    'BaseRule',
    'RequiredColumnRule',
    'NotNullRule',
    'DataTypeRule',
    'MaxLengthRule',
    'ALL_RULES'
]