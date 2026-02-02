# csv_loader/detector.py
"""
Detección estructural del CSV Golden Record.
"""

from typing import List, Tuple, Optional
import csv
from .models import CsvContext, CsvDialectInfo, ErrorSeverity, NormalizedError
from .errors import CsvLoaderErrors


class StructureDetector:
    """Detecta estructura del Golden Record CSV."""
    @classmethod
    def detect_structure(cls, file_path: str, encoding: str, 
                        dialect_info: CsvDialectInfo) -> Tuple[Optional[CsvContext], Optional[NormalizedError]]:
        """
        Detecta la estructura del Golden Record CSV.
        """
        context = CsvContext(encoding=encoding, dialect=dialect_info)
        
        try:
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                csv_reader = csv.reader(f, delimiter=dialect_info.delimiter,
                                    quotechar=dialect_info.quotechar,
                                    escapechar=dialect_info.escapechar,
                                    doublequote=dialect_info.doublequote,
                                    skipinitialspace=dialect_info.skipinitialspace)
                
                rows = []
                for i, row in enumerate(csv_reader):
                    if i >= 3:  # Solo necesitamos 3 filas para detección
                        break
                    rows.append(row)
                
                if not rows:
                    return None, CsvLoaderErrors.empty_file()
                
                # Fila 1: HEADER - Identificadores técnicos
                header_error = cls._validate_header_row(rows[0])
                if header_error:
                    return None, header_error
                
                context.columns = rows[0]
                context.total_columns = len(rows[0])
                
                # **MODIFICACIÓN CRÍTICA:**
                # Para Golden Records, SIEMPRE hay fila de labels después del header
                context.label_row_present = True
                context.data_start_index = 2  # **FORZAR: saltar header(1) + labels(1) = 2**
                
                # Fila 2: LABELS - Validar pero no cambiar data_start_index
                if len(rows) > 1:
                    if len(rows[1]) != context.total_columns:
                        context.errors.append(CsvLoaderErrors.label_column_mismatch(1, context.total_columns, len(rows[1])))
                
                # Fila 3: DATOS - Primera fila de datos
                if len(rows) > 2:
                    data_error = cls._validate_data_row(rows[2], context.total_columns, 2)
                    if data_error:
                        context.errors.append(data_error)
                else:
                    # Si no hay tercera fila, solo datos de ejemplo
                    context.errors.append(CsvLoaderErrors.no_data_rows())
                
                # Logging para debugging
                print(f"   📊 Estructura CSV: {context.total_columns} columnas")
                print(f"   📊 Fila labels: {'SÍ' if context.label_row_present else 'NO'}")
                print(f"   📊 Data start index: {context.data_start_index} (fila {context.data_start_index + 1} del CSV)")
                
                return context, None
                
        except IOError as e:
            return None, NormalizedError(
                code="STRUCTURE_DETECTION_IO_ERROR",
                severity=ErrorSeverity.FATAL,
                message=f"Error de E/S durante detección de estructura: {str(e)}"
            )
        except csv.Error as e:
            return None, NormalizedError(
                code="CSV_PARSING_ERROR",
                severity=ErrorSeverity.FATAL,
                message=f"Error de parsing CSV: {str(e)}"
            )
    @classmethod
    def _validate_header_row(cls, header_row: List[str]) -> Optional[NormalizedError]:
        """Valida la fila de identificadores técnicos."""
        if not header_row:
            return CsvLoaderErrors.missing_header_row()
        
        seen_columns = set()
        
        for i, column in enumerate(header_row):
            # Validar que no esté vacío
            if not column or not str(column).strip():
                return CsvLoaderErrors.empty_column_name(0, i)
            
            column_str = str(column).strip()
            
            # Validar duplicados
            if column_str in seen_columns:
                return CsvLoaderErrors.duplicated_column(0, i, column_str)
            seen_columns.add(column_str)
            
            # Validar patrón básico (debe contener _)
            if '_' not in column_str:
                return CsvLoaderErrors.invalid_column_identifier(0, i, column_str)
        
        return None
    @classmethod
    
    def _looks_like_data_row(cls, row: List[str]) -> bool:
        """
        Determina si una fila parece ser datos (no labels).
        
        Heurística: Las filas de datos suelen tener:
        - Valores vacíos o cortos
        - Fechas, números, booleanos
        - No texto largo descriptivo
        """
        if not row:
            return True
        
        data_indicators = 0
        total_cells = len(row)
        
        for cell in row:
            cell_str = str(cell).strip() if cell else ""
            
            # Indicadores de que es DATO (no label):
            if not cell_str:
                data_indicators += 1  # Vacío = probable dato
            elif cell_str.lower() in ['true', 'false', 'yes', 'no', '0', '1']:
                data_indicators += 1  # Booleano/número = dato
            elif cell_str.replace('-', '').replace('/', '').replace('.', '').isdigit():
                data_indicators += 1  # Fecha/número = dato
            elif len(cell_str) <= 10:
                data_indicators += 1  # Texto corto = probable dato
            # else: Texto largo = probable label
        
        # Si más del 60% de las celdas parecen datos
        return data_indicators > total_cells * 0.6

    
    @classmethod
    def _validate_label_row(cls, label_row: List[str], expected_columns: int) -> Optional[NormalizedError]:
        """Valida la fila de etiquetas."""
        if len(label_row) != expected_columns:
            return CsvLoaderErrors.label_column_mismatch(1, expected_columns, len(label_row))
        
        # Las etiquetas pueden estar vacías, eso es válido
        return None
    
    @classmethod
    def _validate_data_row(cls, data_row: List[str], expected_columns: int, row_index: int) -> Optional[NormalizedError]:
        """Valida una fila de datos."""
        if len(data_row) != expected_columns:
            return CsvLoaderErrors.row_column_mismatch(row_index, expected_columns, len(data_row))
        
        return None