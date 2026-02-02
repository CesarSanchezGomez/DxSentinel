# csv_loader/dialect.py
"""
Detección de dialecto CSV.
"""

import csv
import re
from typing import Tuple, Optional, List
from .models import CsvDialectInfo, ErrorSeverity, NormalizedError
from .errors import CsvLoaderErrors


class DialectDetector:
    """Detecta el dialecto CSV (delimitador, comillas, etc.)."""
    
    # Delimitadores comunes a probar
    COMMON_DELIMITERS = [',', ';', '|', '\t']
    
    # Patrones para detección heurística
    DELIMITER_PATTERNS = [
        (r',(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)', ','),  # Comas fuera de comillas
        (r';(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)', ';'),
        (r'\|(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)', '|'),
        (r'\t', '\t')
    ]
    
    @classmethod
    def detect_dialect(cls, file_path: str, encoding: str) -> Tuple[Optional[CsvDialectInfo], Optional[NormalizedError]]:
        """
        Detecta el dialecto CSV del archivo.
        
        Args:
            file_path: Ruta al archivo
            encoding: Codificación detectada
            
        Returns:
            Tupla (dialect_info, error)
        """
        try:
            # Leer primeras líneas para análisis
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                sample_lines = []
                for _ in range(10):  # Analizar primeras 10 líneas
                    line = f.readline()
                    if not line:
                        break
                    sample_lines.append(line)
                
                if not sample_lines:
                    return None, CsvLoaderErrors.empty_file()
                
                # Método 1: Usar sniffer de csv estándar
                try:
                    sample = ''.join(sample_lines)
                    dialect = csv.Sniffer().sniff(sample, delimiters=''.join(cls.COMMON_DELIMITERS))
                    
                    info = CsvDialectInfo(
                        delimiter=dialect.delimiter,
                        quotechar=dialect.quotechar,
                        doublequote=dialect.doublequote,
                        escapechar=dialect.escapechar,
                        skipinitialspace=dialect.skipinitialspace,
                        lineterminator=dialect.lineterminator,
                        quoting=dialect.quoting
                    )
                    
                    # Validar que el delimitador sea soportado
                    if info.delimiter not in cls.COMMON_DELIMITERS:
                        return None, CsvLoaderErrors.unsupported_csv_dialect(info.delimiter)
                    
                    return info, None
                    
                except csv.Error:
                    # Método 2: Detección heurística
                    return cls._heuristic_detection(sample_lines)
                    
        except IOError as e:
            return None, NormalizedError(
                code="DIALECT_DETECTION_IO_ERROR",
                severity=ErrorSeverity.FATAL,
                message=f"Error de E/S durante detección de dialecto: {str(e)}"
            )
    
    @classmethod
    def _heuristic_detection(cls, sample_lines: List[str]) -> Tuple[Optional[CsvDialectInfo], Optional[NormalizedError]]:
        """Detección heurística de dialecto cuando csv.Sniffer falla."""
        # Contar ocurrencias de delimitadores potenciales
        delimiter_counts = {delim: 0 for delim in cls.COMMON_DELIMITERS}
        
        for line in sample_lines:
            # Ignorar líneas vacías o comentarios
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            for delim in cls.COMMON_DELIMITERS:
                # Contar delimitadores que no estén dentro de comillas
                pattern = re.compile(fr'{re.escape(delim)}(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)')
                delimiter_counts[delim] += len(pattern.findall(line))
        
        # Encontrar el delimitador más común
        most_common = max(delimiter_counts.items(), key=lambda x: x[1])
        
        if most_common[1] == 0:
            # No se detectaron delimitadores, usar comma por defecto
            return CsvDialectInfo(delimiter=','), CsvLoaderErrors.csv_dialect_detection_failed()
        
        # Detectar comillas (simplificado)
        quotechar = '"'
        if any('"' in line for line in sample_lines):
            quotechar = '"'
        elif any("'" in line for line in sample_lines):
            quotechar = "'"
        
        info = CsvDialectInfo(
            delimiter=most_common[0],
            quotechar=quotechar,
            doublequote=True,
            skipinitialspace=False
        )
        
        return info, None