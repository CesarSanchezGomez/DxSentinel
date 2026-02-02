# comparator/models.py
"""
Modelos de datos del comparator.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Set
from enum import Enum


class ValidationSeverity(Enum):
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARNING = "WARNING"


class ValidationScope(Enum):
    GLOBAL = "GLOBAL"        # Aplica a toda la estructura
    ENTITY = "ENTITY"        # Aplica por entidad
    ROW = "ROW"              # Aplica por fila
    FIELD = "FIELD"          # Aplica por campo específico


@dataclass
class ValidationError:
    """Error de validación normalizado."""
    code: str
    severity: ValidationSeverity
    message: str
    scope: ValidationScope
    row_index: Optional[int] = None          # 0-based en datos (sin header)
    csv_row_index: Optional[int] = None      # Índice real en CSV (incluyendo header)
    entity_id: Optional[str] = None
    field_id: Optional[str] = None
    column_name: Optional[str] = None        # Nombre original de columna
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    metadata_path: Optional[str] = None      # Ruta en metadata para debugging
    details: Optional[Dict] = None


@dataclass
class FieldMetadata:
    """Metadata de un campo extraída del árbol XML."""
    element_id: str
    field_id: str
    full_path: str                           # element_id.field_id
    is_required: bool = False
    data_type: Optional[str] = None          # "string", "date", "number", "boolean"
    max_length: Optional[int] = None
    pattern: Optional[str] = None            # Regex pattern
    allowed_values: Optional[List[str]] = None
    is_country_specific: bool = False
    country_code: Optional[str] = None
    metadata_node: Optional[Any] = None      # Nodo XML original para referencia
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityMetadata:
    """Metadata de una entidad."""
    entity_id: str
    fields: Dict[str, FieldMetadata] = field(default_factory=dict)  # field_id -> FieldMetadata
    required_fields: Set[str] = field(default_factory=set)
    is_country_specific: bool = False
    country_code: Optional[str] = None


@dataclass
class MetadataContext:
    """Contexto de metadata para validación."""
    source_instance: str                     # ID de instancia metadata
    source_version: str                      # Versión de metadata
    entities: Dict[str, EntityMetadata] = field(default_factory=dict)  # entity_id -> EntityMetadata
    field_by_full_path: Dict[str, FieldMetadata] = field(default_factory=dict)  # full_path -> FieldMetadata
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationContext:
    """Contexto de validación."""
    transform_context: Any                   # TransformContext del transformer
    metadata_context: MetadataContext
    enabled_rules: List[str] = field(default_factory=lambda: [
        "required_columns",
        "not_null", 
        "data_type",
        "max_length"
    ])
    errors: List[ValidationError] = field(default_factory=list)
    validation_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchValidationResult:
    """Resultado de validación de un lote."""
    batch_index: int
    processed_rows: int
    errors: List[ValidationError]
    validation_time: float = 0.0


@dataclass
class RuleConfiguration:
    """Configuración para una regla."""
    rule_id: str
    enabled: bool = True
    scope: ValidationScope = ValidationScope.FIELD
    params: Dict[str, Any] = field(default_factory=dict)
    error_severity: ValidationSeverity = ValidationSeverity.ERROR