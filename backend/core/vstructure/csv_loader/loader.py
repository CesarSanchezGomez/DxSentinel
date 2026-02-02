# csv_loader/loader.py
"""
Punto de entrada principal del csv_loader.
"""

from typing import Tuple, Optional
from pathlib import Path
from .models import CsvContext
from .encoding import EncodingResolver
from .dialect import DialectDetector
from .detector import StructureDetector
from .reader import BatchReader


class CsvLoader:
    """Carga CSV de Golden Record de forma segura y robusta."""
    
    @classmethod
    def load_csv(cls, file_path: str) -> Tuple[Optional[CsvContext], Optional[str]]:
        """
        Carga un CSV de Golden Record.
        
        Args:
            file_path: Ruta al archivo CSV
            
        Returns:
            Tupla (CsvContext, mensaje_error)
        """
        # Validar que el archivo existe
        if not Path(file_path).exists():
            return None, f"Archivo no encontrado: {file_path}"
        
        # 1. Detectar codificación
        encoding, encoding_error = EncodingResolver.detect_encoding(file_path)
        if encoding_error:
            return None, f"Error de codificación: {encoding_error.message}"
        
        # 2. Detectar dialecto CSV
        dialect_info, dialect_error = DialectDetector.detect_dialect(file_path, encoding)
        if dialect_error:
            return None, f"Error de dialecto CSV: {dialect_error.message}"
        
        # 3. Detectar estructura
        context, structure_error = StructureDetector.detect_structure(file_path, encoding, dialect_info)
        if structure_error:
            return None, f"Error de estructura: {structure_error.message}"
        
        if not context:
            return None, "No se pudo crear contexto CSV"
        
        # 4. Configurar generador de lotes
        batch_generator, read_errors = BatchReader.read_batches(file_path, context)
        context.errors.extend(read_errors)
        
        # Añadir metadata
        context.metadata = {
            'file_path': file_path,
            'file_size': Path(file_path).stat().st_size,
            'encoding_detected': encoding,
            'delimiter': dialect_info.delimiter,
            'total_columns': context.total_columns,
            'has_labels': context.label_row_present
        }
        
        
        # Añadir método para obtener datos por lotes
        context.data_stream = batch_generator 
        
        return context, None