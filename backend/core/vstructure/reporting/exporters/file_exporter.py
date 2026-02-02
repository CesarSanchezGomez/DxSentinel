# src/vstructure/reporting/exporters/file_exporter.py
"""
Exportador de reportes a archivos.
"""

from pathlib import Path
from typing import Optional, Dict, List
from ..models import ValidationReport
from ..errors import ReportingErrors
from vstructure.reporting.formatters.base_formatter import BaseFormatter


class FileExporter:
    """Exporta reportes a archivos."""
    
    @staticmethod
    def export_to_file(
        report: ValidationReport,
        formatted_content: str,
        output_dir: str,
        base_filename: str,
        file_extension: str
    ) -> str:
        """
        Exporta contenido formateado a un archivo.
        
        Args:
            report: Reporte a exportar
            formatted_content: Contenido ya formateado
            output_dir: Directorio de salida
            base_filename: Nombre base del archivo
            file_extension: Extensión del archivo
            
        Returns:
            Ruta del archivo creado
            
        Raises:
            ReportingError si falla la escritura
        """
        try:
            # Crear directorio si no existe
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generar nombre de archivo único
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"{base_filename}_{timestamp}{file_extension}"
            filepath = output_path / filename
            
            # Escribir archivo
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            return str(filepath)
            
        except IOError as e:
            raise ReportingErrors.file_write_failed(
                str(filepath) if 'filepath' in locals() else output_dir,
                str(e)
            )
    
    @staticmethod
    def export_multiple_formats(
        report: ValidationReport,
        formatters: List["BaseFormatter"],
        output_dir: str,
        base_filename: str
    ) -> Dict[str, str]:
        """
        Exporta un reporte en múltiples formatos.
        
        Args:
            report: Reporte a exportar
            formatters: Lista de formateadores
            output_dir: Directorio de salida
            base_filename: Nombre base del archivo
            
        Returns:
            Diccionario formato -> ruta de archivo
        """
        results = {}
        
        for formatter in formatters:
            try:
                # Formatear contenido
                content = formatter.format(report)
                
                # Exportar a archivo
                filepath = FileExporter.export_to_file(
                    report=report,
                    formatted_content=content,
                    output_dir=output_dir,
                    base_filename=base_filename,
                    file_extension=formatter.file_extension
                )
                
                results[formatter.format_name] = filepath
                
            except Exception as e:
                # Continuar con otros formatos si uno falla
                results[formatter.format_name] = f"ERROR: {str(e)}"
        
        return results