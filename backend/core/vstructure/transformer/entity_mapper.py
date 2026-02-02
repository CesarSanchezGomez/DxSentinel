# transformer/entity_mapper.py
"""
Mapeo de columnas a entidades.
"""

from typing import Dict, List, Tuple
from .models import EntityData, ParsedColumn, TransformationError, TransformationSeverity
from .errors import TransformerErrors


class EntityMapper:
    """Agrupa columnas por entidad."""
    
    @staticmethod
    def map_columns_to_entities(parsed_columns: List[ParsedColumn]) -> Tuple[Dict[str, EntityData], List[TransformationError]]:
        """
        Agrupa columnas parseadas por entidad.
        
        Args:
            parsed_columns: Lista de columnas parseadas
            
        Returns:
            Tupla (diccionario de entidades, lista de errores)
        """
        entities: Dict[str, EntityData] = {}
        errors: List[TransformationError] = []
        column_to_entity_map: Dict[int, str] = {}
        
        for col_index, column in enumerate(parsed_columns):
            if not column:
                errors.append(TransformerErrors.invalid_column_composition(
                    f"col_{col_index}", "Columna parseada es None"
                ))
                continue
            
            entity_id = column.element_id
            
            # Crear entidad si no existe
            if entity_id not in entities:
                entities[entity_id] = EntityData(entity_id=entity_id)
            
            # Añadir columna a la entidad
            entities[entity_id].add_column(col_index, column)
            column_to_entity_map[col_index] = entity_id
        
        return entities, column_to_entity_map, errors
    
    @staticmethod
    def validate_entity_structure(entities: Dict[str, EntityData]) -> List[TransformationError]:
        """
        Valida la estructura de las entidades detectadas.
        
        Args:
            entities: Diccionario de entidades
            
        Returns:
            Lista de errores de validación
        """
        errors = []
        
        for entity_id, entity_data in entities.items():
            # Validar que la entidad tenga al menos una columna
            if not entity_data.columns:
                errors.append(TransformationError(
                    code="EMPTY_ENTITY",
                    severity=TransformationSeverity.WARNING,
                    message=f"Entidad '{entity_id}' no tiene columnas asignadas",
                    details={"entity_id": entity_id}
                ))
            
            # Verificar campos duplicados dentro de la misma entidad
            field_counts = {}
            for column in entity_data.columns:
                field_counts[column.field_id] = field_counts.get(column.field_id, 0) + 1
            
            for field_id, count in field_counts.items():
                if count > 1:
                    errors.append(TransformationError(
                        code="DUPLICATE_FIELD_IN_ENTITY",
                        severity=TransformationSeverity.WARNING,
                        message=f"Campo '{field_id}' aparece {count} veces en entidad '{entity_id}'",
                        details={"entity_id": entity_id, "field_id": field_id, "count": count}
                    ))
        
        return errors