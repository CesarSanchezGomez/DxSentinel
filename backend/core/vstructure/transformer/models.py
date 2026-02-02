# transformer/models.py
"""
Modelos de datos del transformer.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from enum import Enum


class TransformationSeverity(Enum):
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass
class TransformationError:
    """Error normalizado del transformer."""
    code: str
    severity: TransformationSeverity
    message: str
    row_index: Optional[int] = None
    column_name: Optional[str] = None
    value: Optional[str] = None
    details: Optional[Dict] = None


@dataclass
class ParsedColumn:
    """Columna parseada desde identificador compuesto."""
    original_name: str
    element_id: str  # Ej: "personInfo", "employmentInfo"
    field_id: str    # Ej: "firstName", "contractReason"
    is_country_specific: bool = False
    country_code: Optional[str] = None
    full_path: str = ""  # element_id.field_id
    
    def __post_init__(self):
        self.full_path = f"{self.element_id}.{self.field_id}"


@dataclass
class EntityData:
    """Datos agrupados por entidad."""
    entity_id: str  # element_id
    columns: List[ParsedColumn] = field(default_factory=list)
    field_mapping: Dict[str, ParsedColumn] = field(default_factory=dict)  # field_id -> ParsedColumn
    column_index_mapping: Dict[int, ParsedColumn] = field(default_factory=dict)  # CSV col index -> ParsedColumn
    
    def add_column(self, index: int, column: ParsedColumn):
        """Añade una columna a la entidad."""
        self.columns.append(column)
        self.field_mapping[column.field_id] = column
        self.column_index_mapping[index] = column


@dataclass
class TransformedRow:
    """Fila transformada con datos organizados por entidad."""
    original_row_index: int  # Índice en el CSV (0-based, incluyendo header y labels)
    csv_row_index: int       # Índice real en datos CSV (2 + n)
    data_by_entity: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # entity_id -> {field_id: value}
    raw_values: List[str] = field(default_factory=list)  # Valores originales intactos
    errors: List[TransformationError] = field(default_factory=list)


@dataclass
class TransformationContext:
    """Contexto final del transformer."""
    csv_context: Any  # CsvContext del loader
    parsed_columns: List[ParsedColumn] = field(default_factory=list)
    entities: Dict[str, EntityData] = field(default_factory=dict)  # entity_id -> EntityData
    column_to_entity_map: Dict[int, str] = field(default_factory=dict)  # col index -> entity_id
    errors: List[TransformationError] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_entity_for_column(self, column_index: int) -> Optional[str]:
        """Obtiene la entidad para un índice de columna."""
        return self.column_to_entity_map.get(column_index)
    
    def get_column_info(self, column_index: int) -> Optional[ParsedColumn]:
        """Obtiene información de columna parseada."""
        entity_id = self.get_entity_for_column(column_index)
        if entity_id and entity_id in self.entities:
            return self.entities[entity_id].column_index_mapping.get(column_index)
        return None


@dataclass
class BatchTransformationResult:
    """Resultado de transformación de un lote."""
    transformed_rows: List[TransformedRow]
    errors: List[TransformationError]
    batch_index: int