# csv_loader/encoding.py
"""
Resolución de codificación de archivos CSV.
"""

import chardet
from typing import Tuple, Optional, BinaryIO
from .models import CsvContext, ErrorSeverity, NormalizedError
from .errors import CsvLoaderErrors


class EncodingResolver:
    """Detecta y resuelve codificación de archivos CSV."""
    
    # Orden de prioridad para detección
    ENCODING_PRIORITY = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    @classmethod
    def detect_encoding(cls, file_path: str) -> Tuple[Optional[str], Optional[NormalizedError]]:
        """
        Detecta la codificación del archivo.
        
        Args:
            file_path: Ruta al archivo CSV
            
        Returns:
            Tupla (encoding, error)
        """
        try:
            # Primero, intentar detectar con chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Leer primeros 10KB para detección
                
                if not raw_data:
                    return None, CsvLoaderErrors.empty_file()
                
                result = chardet.detect(raw_data)
                detected_encoding = result.get('encoding', '').lower()
                confidence = result.get('confidence', 0)
                
                # Si chardet tiene alta confianza, usar esa
                if confidence > 0.7 and detected_encoding:
                    # Normalizar nombres comunes
                    encoding_map = {
                        'utf-8': 'utf-8',
                        'utf-8-sig': 'utf-8-sig',
                        'ascii': 'utf-8',
                        'windows-1252': 'cp1252',
                        'iso-8859-1': 'latin-1'
                    }
                    
                    normalized = encoding_map.get(detected_encoding, detected_encoding)
                    
                    # Verificar que la codificación sea válida
                    try:
                        raw_data.decode(normalized, errors='strict')
                        return normalized, None
                    except (UnicodeDecodeError, LookupError):
                        pass  # Continuar con fallback
                
                # Fallback: intentar cada codificación en orden de prioridad
                for encoding in cls.ENCODING_PRIORITY:
                    try:
                        raw_data.decode(encoding, errors='strict')
                        return encoding, None
                    except (UnicodeDecodeError, LookupError):
                        continue
                
                # Último intento: permitir errores de decodificación
                for encoding in cls.ENCODING_PRIORITY:
                    try:
                        raw_data.decode(encoding, errors='replace')
                        return encoding, CsvLoaderErrors.invalid_characters(0, 0)
                    except LookupError:
                        continue
                
                return None, CsvLoaderErrors.encoding_detection_failed()
                
        except IOError as e:
            return None, NormalizedError(
                code="FILE_IO_ERROR",
                severity=ErrorSeverity.FATAL,
                message=f"Error de E/S al leer archivo: {str(e)}"
            )
    
    @classmethod
    def validate_encoding(cls, file_path: str, encoding: str) -> Optional[NormalizedError]:
        """Valida que todo el archivo pueda leerse con la codificación."""
        try:
            with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                # Leer todo el archivo para validar
                f.read()
            return None
        except UnicodeDecodeError as e:
            return NormalizedError(
                code="ENCODING_VALIDATION_FAILED",
                severity=ErrorSeverity.ERROR,
                message=f"Error de decodificación en línea ~{e.line}: {str(e)}"
            )