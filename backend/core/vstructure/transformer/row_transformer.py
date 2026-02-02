# transformer/row_transformer.py
"""
Transformación de filas CSV a estructura semántica.
"""

from typing import List, Dict, Any
from .models import TransformedRow, EntityData, ParsedColumn, TransformationError
from .errors import TransformerErrors


class RowTransformer:
    """Transforma filas CSV a estructura organizada por entidad."""
    
    @staticmethod
    def transform_row(
        row_values: List[str],
        row_index: int,  # Índice en datos CSV (0 = primera fila de datos)
        csv_start_index: int,  # Índice donde empiezan los datos en CSV (siempre 2)
        column_to_entity_map: Dict[int, str],
        entities: Dict[str, EntityData]
    ) -> TransformedRow:
        """
        Transforma una fila CSV a estructura semántica.
        
        Args:
            row_values: Valores de la fila
            row_index: Índice de la fila en los datos
            csv_start_index: Índice de inicio de datos en CSV
            column_to_entity_map: Mapa columna -> entidad
            entities: Diccionario de entidades
            
        Returns:
            Fila transformada
        """
        transformed_row = TransformedRow(
            original_row_index=row_index,
            csv_row_index=csv_start_index + row_index,
            raw_values=row_values.copy()  # Mantener valores originales intactos
        )
        
        # Inicializar estructura de datos por entidad
        for entity_id in entities.keys():
            transformed_row.data_by_entity[entity_id] = {}
        
        # Procesar cada columna
        for col_index, value in enumerate(row_values):
            if col_index >= len(column_to_entity_map):
                # Columna fuera de rango (error en CSV)
                transformed_row.errors.append(TransformerErrors.row_transformation_error(
                    row_index, col_index, f"Índice de columna {col_index} fuera de rango"
                ))
                continue
            
            entity_id = column_to_entity_map.get(col_index)
            
            if not entity_id:
                # Columna no mapeada a entidad
                transformed_row.errors.append(TransformerErrors.row_transformation_error(
                    row_index, col_index, "Columna no mapeada a entidad"
                ))
                continue
            
            if entity_id not in entities:
                # Entidad no encontrada
                transformed_row.errors.append(TransformerErrors.row_transformation_error(
                    row_index, col_index, f"Entidad '{entity_id}' no encontrada"
                ))
                continue
            
            # Obtener información de la columna
            entity_data = entities[entity_id]
            column_info = entity_data.column_index_mapping.get(col_index)
            
            if not column_info:
                # Columna no encontrada en entidad
                transformed_row.errors.append(TransformerErrors.row_transformation_error(
                    row_index, col_index, f"Columna no encontrada en entidad '{entity_id}'"
                ))
                continue
            
            # Almacenar valor en la estructura de la entidad
            transformed_row.data_by_entity[entity_id][column_info.field_id] = value
        
        return transformed_row
    
    @staticmethod
    def transform_batch(
        batch_rows: List[List[str]],
        batch_index: int,
        csv_start_index: int,
        column_to_entity_map: Dict[int, str],
        entities: Dict[str, EntityData]
    ) -> List[TransformedRow]:
        """
        Transforma un lote de filas.
        
        Args:
            batch_rows: Lote de filas CSV
            batch_index: Índice del lote
            csv_start_index: Índice de inicio de datos en CSV
            column_to_entity_map: Mapa columna -> entidad
            entities: Diccionario de entidades
            
        Returns:
            Lista de filas transformadas
        """
        transformed_rows = []
        
        for row_offset, row_values in enumerate(batch_rows):
            # Calcular índice absoluto de la fila
            absolute_row_index = (batch_index * len(batch_rows)) + row_offset
            
            transformed_row = RowTransformer.transform_row(
                row_values=row_values,
                row_index=absolute_row_index,
                csv_start_index=csv_start_index,
                column_to_entity_map=column_to_entity_map,
                entities=entities
            )
            
            transformed_rows.append(transformed_row)
        
        return transformed_rows