# csv_loader/reader.py
"""
Lectura robusta de CSV por lotes.
"""

import csv
from typing import Iterator, List, Optional, Tuple
from .models import CsvContext, ErrorSeverity, NormalizedError
from .errors import CsvLoaderErrors


class BatchReader:
    """Lee CSV en lotes de forma robusta."""
    
    BATCH_SIZE = 10000
    
    @classmethod
    def read_batches(cls, file_path: str, context: CsvContext) -> Tuple[Iterator[List[List[str]]], List[NormalizedError]]:
        """
        Lee el CSV en lotes, saltando header y labels.
        
        Args:
            file_path: Ruta al archivo
            context: Contexto CSV detectado
            
        Returns:
            Tupla (iterator de lotes, errores de filas)
        """
        errors = []
        batch = []
        
        def batch_generator():
            nonlocal batch, errors
            
            try:
                with open(file_path, 'r', encoding=context.encoding, newline='') as f:
                    csv_reader = csv.reader(f, delimiter=context.dialect.delimiter,
                                           quotechar=context.dialect.quotechar,
                                           escapechar=context.dialect.escapechar,
                                           doublequote=context.dialect.doublequote,
                                           skipinitialspace=context.dialect.skipinitialspace)
                    
                    # Saltar header y labels
                    for _ in range(context.data_start_index):
                        try:
                            next(csv_reader)
                        except StopIteration:
                            break
                    
                    row_index = context.data_start_index
                    
                    for row in csv_reader:
                        # Validar número de columnas
                        if len(row) != context.total_columns:
                            errors.append(
                                CsvLoaderErrors.row_column_mismatch(
                                    row_index, 
                                    context.total_columns, 
                                    len(row)
                                )
                            )
                            row_index += 1
                            continue
                        
                        # Añadir a lote actual
                        batch.append(row)
                        
                        # Entregar lote cuando alcance tamaño
                        if len(batch) >= cls.BATCH_SIZE:
                            yield batch
                            batch = []
                        
                        row_index += 1
                    
                    # Entregar último lote (si hay)
                    if batch:
                        yield batch
                        
            except IOError as e:
                errors.append(NormalizedError(
                    code="BATCH_READER_IO_ERROR",
                    severity=ErrorSeverity.FATAL,
                    message=f"Error de E/S durante lectura por lotes: {str(e)}"
                ))
            except csv.Error as e:
                errors.append(NormalizedError(
                    code="CSV_READING_ERROR",
                    severity=ErrorSeverity.FATAL,
                    message=f"Error de lectura CSV: {str(e)}"
                ))
        
        return batch_generator(), errors