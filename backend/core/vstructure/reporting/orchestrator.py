# reporting/orchestrator.py - CORREGIDO
"""
Orquestador principal del módulo reporting.
CORREGIDO: Eliminar importación circular.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from .models import ValidationReport, ReportFormat
from .aggregator import ReportAggregator
from .formatters import JSONFormatter, CSVFormatter
from .exporters import FileExporter
from .errors import ReportingErrors


class ReportingOrchestrator:
    """Orquestador para generación de reportes."""
    
    def __init__(self):
        self.formatters = {
            ReportFormat.JSON.value: JSONFormatter(),
            ReportFormat.CSV.value: CSVFormatter()
        }
    
    def generate_report(
        self,
        batch_results: List[Any],  # Cambiado de BatchValidationResult a Any para evitar importación circular
        source_csv: str,
        source_metadata: str,
        validation_stats: Dict[str, Any]
    ) -> ValidationReport:
        """
        Genera un reporte de validación.
        
        Args:
            batch_results: Resultados de validación por lote (cualquier tipo)
            source_csv: Ruta o nombre del CSV fuente
            source_metadata: Identificador de metadata fuente
            validation_stats: Estadísticas de validación
            
        Returns:
            Reporte de validación
        """
        print("📊 Generando reporte de validación...")
        
        # Crear reporte estructurado
        report = ReportAggregator.create_report(
            batch_results=batch_results,
            source_csv=source_csv,
            source_metadata=source_metadata,
            validation_stats=validation_stats
        )
        
        print(f"   ✓ Reporte ID: {report.report_id}")
        print(f"   ✓ Entradas: {len(report.entries)}")
        print(f"   ✓ Errores: {report.metrics.total_errors}")
        print(f"   ✓ Advertencias: {report.metrics.total_warnings}")
        print(f"   📋 Resumen: {report.summary}")
        
        return report
    
    def export_report(
        self,
        report: ValidationReport,
        output_dir: str,
        base_filename: Optional[str] = None,
        formats: List[str] = None
    ) -> Dict[str, str]:
        """
        Exporta un reporte a archivos.
        
        Args:
            report: Reporte a exportar
            output_dir: Directorio de salida
            base_filename: Nombre base del archivo (opcional)
            formats: Lista de formatos a exportar
            
        Returns:
            Diccionario formato -> ruta de archivo
        """
        if formats is None:
            formats = [ReportFormat.JSON.value, ReportFormat.CSV.value]
        
        if base_filename is None:
            base_filename = f"validation_report_{report.report_id}"
        
        print(f"💾 Exportando reporte a {output_dir}...")
        
        # Seleccionar formateadores
        selected_formatters = []
        for format_name in formats:
            if format_name in self.formatters:
                selected_formatters.append(self.formatters[format_name])
            else:
                print(f"   ⚠ Formato no soportado: {format_name}")
        
        if not selected_formatters:
            raise ReportingErrors.invalid_format(str(formats))
        
        # Exportar a archivos
        try:
            results = FileExporter.export_multiple_formats(
                report=report,
                formatters=selected_formatters,
                output_dir=output_dir,
                base_filename=base_filename
            )
            
            # Mostrar resultados
            for format_name, filepath in results.items():
                if filepath.startswith("ERROR:"):
                    print(f"   ❌ {format_name}: {filepath}")
                else:
                    print(f"   ✓ {format_name}: {filepath}")
            
            return results
            
        except Exception as e:
            raise ReportingErrors.export_failed(str(formats), str(e))
    
    def export_to_string(
        self,
        report: ValidationReport,
        format_name: str = "json"
    ) -> str:
        """
        Exporta un reporte a string en el formato especificado.
        
        Args:
            report: Reporte a exportar
            format_name: Nombre del formato
            
        Returns:
            String con el reporte formateado
        """
        if format_name not in self.formatters:
            raise ReportingErrors.invalid_format(format_name)
        
        formatter = self.formatters[format_name]
        return formatter.format(report)
    
    def generate_and_export(
        self,
        batch_results: List[Any],
        source_csv: str,
        source_metadata: str,
        validation_stats: Dict[str, Any],
        output_dir: str,
        base_filename: Optional[str] = None,
        formats: List[str] = None
    ) -> Dict[str, Any]:
        """
        Genera y exporta un reporte en un solo paso.
        
        Args:
            batch_results: Resultados de validación
            source_csv: Ruta del CSV fuente
            source_metadata: Identificador de metadata
            validation_stats: Estadísticas de validación
            output_dir: Directorio de salida
            base_filename: Nombre base del archivo
            formats: Formatos a exportar
            
        Returns:
            Diccionario con reporte y rutas de archivo
        """
        # Generar reporte
        report = self.generate_report(
            batch_results=batch_results,
            source_csv=source_csv,
            source_metadata=source_metadata,
            validation_stats=validation_stats
        )
        
        # Exportar reporte
        filepaths = self.export_report(
            report=report,
            output_dir=output_dir,
            base_filename=base_filename,
            formats=formats
        )
        
        return {
            "report": report,
            "filepaths": filepaths,
            "report_id": report.report_id,
            "summary": report.summary
        }
    
    def quick_summary(
        self,
        batch_results: List[Any],
        validation_stats: Dict[str, Any]
    ) -> str:
        """
        Genera un resumen rápido de la validación.
        
        Args:
            batch_results: Resultados de validación
            validation_stats: Estadísticas de validación
            
        Returns:
            String con resumen
        """
        # Calcular métricas rápidas usando type hints dinámicos
        total_errors = 0
        total_warnings = 0
        total_rows = validation_stats.get("total_rows", 0)
        
        for batch_result in batch_results:
            for error in getattr(batch_result, 'errors', []):
                severity = getattr(error, 'severity', None)
                if severity:
                    severity_value = getattr(severity, 'value', str(severity))
                    if severity_value in ["ERROR", "FATAL"]:
                        total_errors += 1
                    elif severity_value == "WARNING":
                        total_warnings += 1
        
        if total_errors == 0 and total_warnings == 0:
            return f"✅ Validación exitosa: {total_rows} filas sin errores."
        
        return (
            f"📊 Resumen validación: {total_rows} filas, "
            f"{total_errors} errores, {total_warnings} advertencias."
        )