# transformer/context_builder.py
"""
Construcción del contexto final de transformación.
"""

from typing import Dict, List, Any
from .models import TransformationContext, EntityData, ParsedColumn, BatchTransformationResult, TransformationError, TransformedRow


class ContextBuilder:
    """Construye el contexto final del transformer."""
    
    @staticmethod
    def build_context(
        csv_context: Any,
        parsed_columns: List[ParsedColumn],
        entities: Dict[str, EntityData],
        column_to_entity_map: Dict[int, str],
        transformation_errors: List[TransformationError]
    ) -> TransformationContext:
        """
        Construye el contexto de transformación.
        
        Args:
            csv_context: Contexto CSV del loader
            parsed_columns: Columnas parseadas
            entities: Entidades mapeadas
            column_to_entity_map: Mapa columna -> entidad
            transformation_errors: Errores de transformación
            
        Returns:
            Contexto de transformación completo
        """
        context = TransformationContext(
            csv_context=csv_context,
            parsed_columns=parsed_columns,
            entities=entities,
            column_to_entity_map=column_to_entity_map,
            errors=transformation_errors
        )
        
        # Añadir metadata adicional
        context.metadata = {
            'total_columns': len(parsed_columns),
            'total_entities': len(entities),
            'entity_ids': list(entities.keys()),
            'country_specific_columns': [
                col.original_name for col in parsed_columns 
                if col.is_country_specific
            ],
            'has_transformation_errors': len(transformation_errors) > 0,
            'error_count': len(transformation_errors)
        }
        
        return context
    
    @staticmethod
    def create_batch_result(
        transformed_rows: List[TransformedRow],
        errors: List[TransformationError],
        batch_index: int
    ) -> BatchTransformationResult:
        """
        Crea un resultado de lote transformado.
        
        Args:
            transformed_rows: Filas transformadas
            errors: Errores del lote
            batch_index: Índice del lote
            
        Returns:
            Resultado del lote
        """
        return BatchTransformationResult(
            transformed_rows=transformed_rows,
            errors=errors,
            batch_index=batch_index
        )