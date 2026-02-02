# transformer/orchestrator.py
"""
Punto de entrada principal del transformer.
"""

from typing import Tuple, Optional, Iterator, List

from realtime import Any
from .models import TransformationContext, BatchTransformationResult
from .column_parser import ColumnParser
from .entity_mapper import EntityMapper
from .row_transformer import RowTransformer
from .context_builder import ContextBuilder
from .errors import TransformerErrors


class TransformationOrchestrator:
    """Orquestador principal del transformer."""
    
    @classmethod
    def transform_csv_context(cls, csv_context: Any) -> Tuple[Optional[TransformationContext], Optional[str]]:
        """
        Transforma el contexto CSV a estructura semántica.
        
        Args:
            csv_context: Contexto CSV del loader
            
        Returns:
            Tupla (TransformationContext, mensaje_error)
        """
        try:
            # 1. Parsear todas las columnas
            parsed_columns, parse_errors = ColumnParser.parse_all_columns(csv_context.columns)
            
            if not parsed_columns:
                return None, "No se pudieron parsear columnas del CSV"
            
            # 2. Mapear columnas a entidades
            entities, column_to_entity_map, mapping_errors = EntityMapper.map_columns_to_entities(parsed_columns)
            
            # 3. Validar estructura de entidades
            validation_errors = EntityMapper.validate_entity_structure(entities)
            
            # Combinar todos los errores
            all_errors = parse_errors + mapping_errors + validation_errors
            
            # 4. Construir contexto de transformación
            context = ContextBuilder.build_context(
                csv_context=csv_context,
                parsed_columns=parsed_columns,
                entities=entities,
                column_to_entity_map=column_to_entity_map,
                transformation_errors=all_errors
            )
            
            # 5. Añadir método para transformar lotes
            context.transform_batch = lambda batch_data, batch_index: cls._transform_batch(
                batch_data, batch_index, context
            )
            
            return context, None
            
        except Exception as e:
            return None, f"Error fatal en transformación: {str(e)}"
    
    @classmethod
    def _transform_batch(
        cls,
        batch_rows: List[List[str]],
        batch_index: int,
        context: TransformationContext
    ) -> BatchTransformationResult:
        """
        Transforma un lote de filas CSV.
        
        Args:
            batch_rows: Lote de filas CSV
            batch_index: Índice del lote
            context: Contexto de transformación
            
        Returns:
            Resultado del lote transformado
        """
        try:
            transformed_rows = RowTransformer.transform_batch(
                batch_rows=batch_rows,
                batch_index=batch_index,
                csv_start_index=context.csv_context.data_start_index,
                column_to_entity_map=context.column_to_entity_map,
                entities=context.entities
            )
            
            # Recopilar errores de todas las filas
            batch_errors = []
            for row in transformed_rows:
                batch_errors.extend(row.errors)
            
            return ContextBuilder.create_batch_result(
                transformed_rows=transformed_rows,
                errors=batch_errors,
                batch_index=batch_index
            )
            
        except Exception as e:
            # Crear resultado de error
            return BatchTransformationResult(
                transformed_rows=[],
                errors=[TransformerErrors.transformation_failed(
                    batch_index * len(batch_rows),
                    f"Error en lote {batch_index}: {str(e)}"
                )],
                batch_index=batch_index
            )