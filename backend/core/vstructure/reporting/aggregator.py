# reporting/aggregator.py - CORREGIDO

"""
Agregador de métricas y resultados.
CORREGIDO: Eliminar importación circular.
ACTUALIZADO: Usar personInfo_person-id-external como identificador.
"""

from typing import List, Dict, Any
from datetime import datetime
from .models import (
    ValidationReport, ReportEntry, ValidationMetrics, 
    ReportLevel
)


class ReportAggregator:
    """Agrega resultados de validación en un reporte estructurado."""
    
    @staticmethod
    def create_report(
        batch_results: List[Any],
        source_csv: str,
        source_metadata: str,
        validation_stats: Dict[str, Any]
    ) -> ValidationReport:
        """
        Crea un reporte de validación a partir de resultados por lote.
        
        Args:
            batch_results: Resultados de validación por lote (cualquier tipo)
            source_csv: Ruta o nombre del CSV fuente
            source_metadata: Identificador de metadata fuente
            validation_stats: Estadísticas de validación
            
        Returns:
            Reporte de validación estructurado
        """
        # Generar ID único para el reporte
        report_id = f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Crear reporte base
        report = ValidationReport(
            report_id=report_id,
            timestamp=datetime.now(),
            source_csv=source_csv,
            source_metadata=source_metadata
        )
        
        # Procesar todos los errores de todos los lotes usando atributos dinámicos
        all_errors = []
        for batch_result in batch_results:
            errors = getattr(batch_result, 'errors', [])
            all_errors.extend(errors)
        
        # Convertir errores a entradas de reporte
        report.entries = ReportAggregator._convert_errors_to_entries(all_errors)
        
        # Calcular métricas
        report.metrics = ReportAggregator._calculate_metrics(
            batch_results, validation_stats
        )
        
        # Generar resumen
        report.summary = ReportAggregator._generate_summary(report.metrics)
        
        return report
    
    @staticmethod
    def _convert_errors_to_entries(
        validation_errors: List[Any]
    ) -> List[ReportEntry]:
        """Convierte errores de validación a entradas de reporte."""
        entries = []
        
        for error in validation_errors:
            # Extraer atributos dinámicamente
            person_id_external = getattr(error, 'person_id_external', None)
            field_id = getattr(error, 'field_id', None)
            column_name = getattr(error, 'column_name', None)
            error_code = getattr(error, 'code', 'UNKNOWN_ERROR')
            message = getattr(error, 'message', 'Error desconocido')
            severity = getattr(error, 'severity', None)
            expected = getattr(error, 'expected', None)
            actual = getattr(error, 'actual', None)
            metadata_path = getattr(error, 'metadata_path', None)
            details = getattr(error, 'details', None)
            
            # Mapear severidad a ReportLevel
            level = ReportLevel.INFO
            if severity:
                severity_str = str(severity)
                if "ERROR" in severity_str or "FATAL" in severity_str:
                    level = ReportLevel.ERROR
                elif "WARNING" in severity_str:
                    level = ReportLevel.WARNING
            
            entry = ReportEntry(
                identificador=person_id_external,  # <-- Usar valor real
                field_id=field_id,
                column_name=column_name,
                error_code=error_code,
                message=message,
                level=level,
                expected=expected,
                actual=actual,
                metadata_path=metadata_path,
                details=details
            )
            
            entries.append(entry)
        
        return entries
    
    @staticmethod
    def _calculate_metrics(
        batch_results: List[Any],
        validation_stats: Dict[str, Any]
    ) -> ValidationMetrics:
        """Calcula métricas de validación."""
        metrics = ValidationMetrics()
        
        # Procesar todos los lotes
        all_errors = []
        for batch_result in batch_results:
            metrics.total_batches += 1
            metrics.total_rows += getattr(batch_result, 'processed_rows', 0)
            metrics.validation_time += getattr(batch_result, 'validation_time', 0.0)
            
            errors = getattr(batch_result, 'errors', [])
            all_errors.extend(errors)
        
        # Contar errores y warnings
        for error in all_errors:
            # Extraer severidad dinámicamente
            severity = getattr(error, 'severity', None)
            error_code = getattr(error, 'code', 'UNKNOWN')
            
            # Contar por severidad
            if severity:
                severity_value = getattr(severity, 'value', str(severity))
                metrics.severity_counts[severity_value] = (
                    metrics.severity_counts.get(severity_value, 0) + 1
                )
                
                if severity_value in ["ERROR", "FATAL"]:
                    metrics.total_errors += 1
                elif severity_value == "WARNING":
                    metrics.total_warnings += 1
            
            # Contar por tipo de error
            metrics.error_counts[error_code] = (
                metrics.error_counts.get(error_code, 0) + 1
            )
            
            # Contar por identificador
            identificador = "personInfo_person-id-external"
            metrics.identificador_counts[identificador] = (
                metrics.identificador_counts.get(identificador, 0) + 1
            )
        
        return metrics
    
    @staticmethod
    def _generate_summary(metrics: ValidationMetrics) -> str:
        """Genera un resumen textual de las métricas."""
        if metrics.total_errors == 0 and metrics.total_warnings == 0:
            return "✅ Validación completada sin errores ni advertencias."
        
        summary_parts = []
        
        if metrics.total_errors > 0:
            summary_parts.append(f"❌ {metrics.total_errors} errores")
        
        if metrics.total_warnings > 0:
            summary_parts.append(f"⚠️ {metrics.total_warnings} advertencias")
        
        summary = f"Validación completada con {' y '.join(summary_parts)}."
        
        # Añadir errores más comunes
        if metrics.error_counts:
            top_errors = sorted(
                metrics.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            summary += f" Errores más frecuentes: {', '.join([f'{code} ({count})' for code, count in top_errors])}."
        
        return summary
    
    @staticmethod
    def generate_detailed_report(
        report: ValidationReport,
        max_entries: int = 1000
    ) -> Dict[str, Any]:
        """
        Genera un reporte detallado con análisis adicional.
        
        Args:
            report: Reporte base
            max_entries: Máximo de entradas a incluir (para performance)
            
        Returns:
            Diccionario con reporte detallado
        """
        detailed = report.to_dict()
        
        # Análisis por identificador
        identificador_analysis = {}
        for entry in report.entries:
            if entry.identificador:
                if entry.identificador not in identificador_analysis:
                    identificador_analysis[entry.identificador] = {
                        "total_errors": 0,
                        "total_warnings": 0,
                        "field_counts": {},
                        "error_types": {}
                    }
                
                analysis = identificador_analysis[entry.identificador]
                
                if entry.level == ReportLevel.ERROR:
                    analysis["total_errors"] += 1
                elif entry.level == ReportLevel.WARNING:
                    analysis["total_warnings"] += 1
                
                # Contar por campo
                if entry.field_id:
                    analysis["field_counts"][entry.field_id] = (
                        analysis["field_counts"].get(entry.field_id, 0) + 1
                    )
                
                # Contar por tipo de error
                analysis["error_types"][entry.error_code] = (
                    analysis["error_types"].get(entry.error_code, 0) + 1
                )
        
        detailed["identificador_analysis"] = identificador_analysis
        
        # Limitar entradas si son muchas
        if len(report.entries) > max_entries:
            detailed["entries"] = detailed["entries"][:max_entries]
            detailed["entries_truncated"] = True
            detailed["total_entries_truncated"] = len(report.entries) - max_entries
        else:
            detailed["entries_truncated"] = False
        
        return detailed