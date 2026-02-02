# src/vstructure/orchestrator.py - CORREGIDO
"""
Orquestador principal del sistema de validación estructural.
ACTUALIZADO: Pasa parsed_metadata al comparador.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import traceback
import json

# Importar módulos internos
from .csv_loader import CsvLoader
from .transformer import TransformationOrchestrator
from .comparator import ComparisonOrchestrator
from .reporting import ReportingOrchestrator


class ValidationOrchestrator:
    """
    Orquestador principal que coordina todos los módulos del validador.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el orquestador con configuración.
        
        Args:
            config: Configuración del sistema
        """
        self.config = config or {}
        
        # Inicializar módulos
        self.csv_loader = CsvLoader
        self.transformer = TransformationOrchestrator
        self.comparator = ComparisonOrchestrator()
        self.reporter = ReportingOrchestrator()
        
        # Estado de ejecución
        self.execution_id = None
        self.start_time = None
        self.end_time = None
        
    def execute_validation(
        self,
        instance_id: str,
        version: str,
        golden_record: str,
        report_formats: Optional[List[str]] = None,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta validación completa con los nuevos parámetros.
        
        Args:
            instance_id: ID de la instancia (ej: SF12321)
            version: Versión específica (ej: 20260201_v1)
            golden_record: Ruta al CSV Golden Record
            report_formats: Formatos de reporte (json, csv) - solo para formato en memoria
            
        Returns:
            Diccionario con resultados de validación y reporte en memoria
        """
        if output_dir is None:
            output_dir = self._get_persistent_output_dir()
    
        # Configurar valores por defecto
        if report_formats is None:
            report_formats = ["json", "csv"]
        
        # Iniciar ejecución
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now()
        
        print(f"\n{'='*80}")
        print(f"🚀 INICIANDO VALIDACIÓN ESTRUCTURAL")
        print(f"   Instancia: {instance_id}")
        print(f"   Versión: {version}")
        print(f"   Golden Record: {golden_record}")
        print(f"{'='*80}")
        
        results = {
            "execution_id": self.execution_id,
            "start_time": self.start_time.isoformat(),
            "instance_id": instance_id,
            "version": version,
            "golden_record_path": golden_record,
            "success": False,
            "errors": [],
            "warnings": [],
            "report": None,  # Reporte en memoria
            "summary": {}
        }
        
        try:
            # PASO 1: Cargar CSV Golden Record
            print(f"\n📥 1. CARGANDO CSV GOLDEN RECORD")
            print(f"   Archivo: {golden_record}")
            
            csv_context, csv_error = self.csv_loader.load_csv(golden_record)
            if csv_error:
                raise Exception(f"Error cargando CSV: {csv_error}")
            
            print(f"   ✓ Columnas detectadas: {csv_context.total_columns}")
            print(f"   ✓ Encoding: {csv_context.encoding}")
            print(f"   ✓ Delimitador: {repr(csv_context.dialect.delimiter)}")
            
            if csv_context.errors:
                print(f"   ⚠ Advertencias en carga: {len(csv_context.errors)}")
                results["warnings"].extend([
                    {"module": "csv_loader", "error": err.message}
                    for err in csv_context.errors
                ])
            
            # PASO 2: Cargar metadata parseada usando instance_id y version
            print(f"\n📋 2. CARGANDO METADATA PARSEADA")
            print(f"   Instancia: {instance_id}")
            print(f"   Versión: {version}")
            
            parsed_metadata = self._load_parsed_metadata(instance_id, version)
            
            if not parsed_metadata:
                raise Exception("No se pudo cargar metadata parseada")
            
            print(f"   ✓ Metadata cargada correctamente")
            metadata_info = parsed_metadata.get('metadata', {})
            print(f"   ✓ Origen: {metadata_info.get('instance_id', 'N/A')}")
            print(f"   ✓ Fecha creación: {metadata_info.get('creation_date', 'N/A')}")
            
            # PASO 3: Transformar CSV a estructura semántica
            print(f"\n🔄 3. TRANSFORMANDO ESTRUCTURA CSV")
            
            trans_context, trans_error = self.transformer.transform_csv_context(csv_context)
            if trans_error:
                raise Exception(f"Error transformando CSV: {trans_error}")
            
            print(f"   ✓ Entidades detectadas: {len(trans_context.entities)}")
            print(f"   ✓ Columnas parseadas: {len(trans_context.parsed_columns)}")
            
            if trans_context.errors:
                print(f"   ⚠ Advertencias en transformación: {len(trans_context.errors)}")
                results["warnings"].extend([
                    {"module": "transformer", "error": err.message}
                    for err in trans_context.errors
                ])
            
            # PASO 4: Crear contexto de validación con parsed_metadata
            print(f"\n⚖️  4. PREPARANDO VALIDACIÓN")
            
            validation_context, val_error = self.comparator.create_validation_context(
                transform_context=trans_context,
                metadata_instance_id=instance_id,
                metadata_version=version,
                parsed_metadata=parsed_metadata  # <-- CORRECCIÓN: Pasar parsed_metadata
            )
            
            if val_error:
                raise Exception(f"Error preparando validación: {val_error}")
            
            print(f"   ✓ Contexto de validación creado")
            print(f"   ✓ Reglas habilitadas: {len(validation_context.enabled_rules)}")
            
            # PASO 5: Ejecutar validación
            print(f"\n🔍 5. EJECUTANDO VALIDACIONES")
            print("   Procesando datos...")
            
            batch_results = []
            data_stream = csv_context.data_stream
            batch_index = 0
            
            for raw_batch in data_stream:
                # Transformar lote
                batch_transform = trans_context.transform_batch(raw_batch, batch_index)
                
                # Validar lote
                batch_result = self._validate_batch_directly(
                    batch_transform.transformed_rows,
                    batch_index,
                    validation_context
                )
                
                batch_results.append(batch_result)
                batch_index += 1
                
                # Mostrar progreso
                if batch_index % 5 == 0 or batch_index == 1:
                    processed_rows = sum(br.processed_rows for br in batch_results)
                    total_errors = sum(len(br.errors) for br in batch_results)
                    print(f"   Procesados: {processed_rows} filas, {batch_index} lotes, {total_errors} errores")
            
            # Estadísticas de validación
            validation_stats = {
                "total_rows": sum(br.processed_rows for br in batch_results),
                "total_batches": len(batch_results),
                "total_errors": sum(len(br.errors) for br in batch_results),
                "validation_time": sum(br.validation_time for br in batch_results),
                "csv_columns": csv_context.total_columns,
                "csv_entities": len(trans_context.entities),
                "metadata_entities": len(validation_context.metadata_context.entities) if hasattr(validation_context, 'metadata_context') else 0
            }
            
            print(f"\n   📊 Estadísticas:")
            print(f"      Filas procesadas: {validation_stats['total_rows']}")
            print(f"      Lotes procesados: {validation_stats['total_batches']}")
            print(f"      Errores encontrados: {validation_stats['total_errors']}")
            
            # PASO 6: Generar reportes EN MEMORIA (sin guardar archivos)
            print(f"\n📊 6. GENERANDO REPORTES EN MEMORIA")
            
            # Crear un directorio temporal para la generación del reporte
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                # Generar reportes en el directorio temporal
                report_results = self.reporter.generate_and_export(
                    batch_results=batch_results,
                    source_csv=golden_record,
                    source_metadata=f"{instance_id}_{version}",
                    validation_stats=validation_stats,
                    output_dir=output_dir,
                    base_filename=f"validation_{self.execution_id}",
                    formats=report_formats
                )
                
                # Cargar el reporte JSON en memoria
                json_report_path = report_results.get("filepaths", {}).get("json")
                if json_report_path and Path(json_report_path).exists():
                    with open(json_report_path, 'r', encoding='utf-8') as f:
                        results["report"] = json.load(f)
                
                results["summary"] = report_results["summary"]
                results["success"] = True
                
                print(f"\n   ✅ Reporte generado en memoria")
                print(f"   📋 Resumen final: {results['summary']}")
            
        except Exception as e:
            # Capturar error y registrar
            error_info = {
                "module": "orchestrator",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            results["errors"].append(error_info)
            
            print(f"\n❌ ERROR EN EJECUCIÓN: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
            
        finally:
            # Finalizar ejecución
            self.end_time = datetime.now()
            execution_time = (self.end_time - self.start_time).total_seconds()
            
            results["end_time"] = self.end_time.isoformat()
            results["execution_time_seconds"] = execution_time
            
            print(f"\n{'='*80}")
            print(f"🏁 VALIDACIÓN COMPLETADA - Tiempo: {execution_time:.2f}s")
            print(f"{'='*80}")
            
        return results
    
# src/vstructure/orchestrator.py - CORRECCIÓN: Cargar PICKLE, no JSON
    def _get_persistent_output_dir(self) -> str:
        """Obtiene directorio persistente para guardar reportes"""
        base_dir = Path("backend/storage/reports")
        base_dir.mkdir(parents=True, exist_ok=True)
        return str(base_dir)
    
    def _load_parsed_metadata(
        self, 
        instance_id: str, 
        version: str
    ) -> Optional[Dict[str, Any]]:
        """
        Carga metadata ya parseada desde la nueva estructura.
        
        Args:
            instance_id: ID de la instancia (ej: SF12321)
            version: Versión específica (ej: 20260201_v1)
            
        Returns:
            Metadata parseada o None si error
            
        Estructura esperada:
        backend/storage/metadata/{instance_id}/{version}/
        ├── document_{instance_id}.json
        ├── document_{instance_id}.pkl  <-- ESTE ES EL IMPORTANTE
        └── metadata_{instance_id}.json
        """
        try:
            # Buscar en la nueva estructura de metadata
            metadata_base = Path("backend/storage/metadata")
            
            if not metadata_base.exists():
                # Intentar estructuras alternativas si no existe
                metadata_base = Path("storage/metadata")
                if not metadata_base.exists():
                    metadata_base = Path("metadata")
            
            print(f"   Buscando en: {metadata_base}")
            
            # Buscar instancia
            instance_path = metadata_base / instance_id
            if not instance_path.exists():
                raise FileNotFoundError(f"Instancia metadata no encontrada: {instance_id}")
            print(f"   ✓ Instancia encontrada: {instance_path}")
            
            # Buscar versión específica
            version_path = instance_path / version
            if not version_path.exists():
                raise FileNotFoundError(f"Versión metadata no encontrada: {version}")
            print(f"   ✓ Versión encontrada: {version_path}")
            
            # Buscar archivos disponibles
            files_in_version = list(version_path.glob("*"))
            print(f"   Archivos en versión: {[f.name for f in files_in_version]}")
            
            # CORRECCIÓN: Cargar el archivo PICKLE (XMLDocument serializado)
            pickle_file_pattern = f"document_{instance_id}.pkl"
            pickle_file = version_path / pickle_file_pattern
            
            # Si no existe con el patrón, buscar cualquier document_*.pkl
            if not pickle_file.exists():
                pickle_files = list(version_path.glob("document_*.pkl"))
                if pickle_files:
                    pickle_file = pickle_files[0]
                    print(f"   Usando archivo pickle alternativo: {pickle_file.name}")
                else:
                    raise FileNotFoundError(f"Archivo document_*.pkl no encontrado en: {version_path}")
            
            print(f"   Cargando PICKLE: {pickle_file}")
            
            # Cargar el objeto XMLDocument serializado
            import pickle
            with open(pickle_file, 'rb') as f:
                xml_document = pickle.load(f)
            
            # Ahora necesitamos convertir el XMLDocument a un diccionario
            # que pueda ser procesado por MetadataAdapter.adapt_parsed_metadata
            
            # Crear una estructura compatible con lo que espera MetadataAdapter
            parsed_data = {
                "metadata": {},
                "structure": self._xml_document_to_dict(xml_document)
            }
            
            # Intentar cargar metadata.json para información adicional
            metadata_file_pattern = f"metadata_{instance_id}.json"
            metadata_file = version_path / metadata_file_pattern
            
            # Si no existe con el patrón, buscar cualquier metadata_*.json
            if not metadata_file.exists():
                metadata_files = list(version_path.glob("metadata_*.json"))
                if metadata_files:
                    metadata_file = metadata_files[0]
            
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_info = json.load(f)
                
                # Añadir información de metadata
                parsed_data["metadata"] = metadata_info
                
                print(f"   ✓ Metadata adicional cargada: {metadata_file.name}")
            
            # Añadir información básica si no existe
            if "instance_id" not in parsed_data["metadata"]:
                parsed_data["metadata"]["instance_id"] = instance_id
            if "version" not in parsed_data["metadata"]:
                parsed_data["metadata"]["version"] = version
            
            print(f"   ✓ Metadata PICKLE cargada correctamente")
            print(f"   ✓ Objeto XMLDocument cargado")
            
            return parsed_data
            
        except Exception as e:
            print(f"   ❌ Error cargando metadata: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
            return None
    
    def _xml_document_to_dict(self, xml_document) -> Dict[str, Any]:
        """
        Convierte un objeto XMLDocument a un diccionario compatible.
        
        Args:
            xml_document: Objeto XMLDocument serializado
            
        Returns:
            Diccionario con la estructura del documento
        """
        try:
            # Función recursiva para convertir nodos
            def node_to_dict(node):
                result = {}
                
                # Extraer propiedades básicas del nodo
                if hasattr(node, 'tag'):
                    result['tag'] = node.tag
                if hasattr(node, 'technical_id'):
                    result['technical_id'] = node.technical_id
                if hasattr(node, 'node_type'):
                    # Convertir node_type Enum a string
                    node_type = node.node_type
                    if hasattr(node_type, 'value'):
                        result['node_type'] = node_type.value
                    else:
                        result['node_type'] = str(node_type)
                
                # Extraer atributos
                if hasattr(node, 'attributes'):
                    result['attributes'] = dict(node.attributes)
                
                # Procesar hijos recursivamente
                if hasattr(node, 'children'):
                    children = []
                    for child in node.children:
                        child_dict = node_to_dict(child)
                        if child_dict:
                            children.append(child_dict)
                    if children:
                        result['children'] = children
                
                return result
            
            # Procesar el root del documento
            if hasattr(xml_document, 'root'):
                return node_to_dict(xml_document.root)
            else:
                print("   ⚠ XMLDocument no tiene atributo 'root'")
                return {}
                
        except Exception as e:
            print(f"   ⚠ Error convirtiendo XMLDocument a dict: {e}")
            return {}
    
    def _validate_batch_directly(
        self,
        transformed_rows: List,
        batch_index: int,
        validation_context: Any
    ) -> Any:
        """
        Valida un lote directamente usando el RuleEngine.
        
        Args:
            transformed_rows: Filas transformadas
            batch_index: Índice del lote
            validation_context: Contexto de validación
            
        Returns:
            BatchValidationResult
        """
        from .comparator import RuleEngine, RuleRegistry
        
        # Crear rule engine
        rule_registry = RuleRegistry()
        rule_engine = RuleEngine(rule_registry)
        
        # Validar lote
        return rule_engine.validate_batch(
            batch_rows=transformed_rows,
            batch_index=batch_index,
            context=validation_context
        )
    
    def _find_latest_version(self, instance_path: Path) -> Optional[str]:
        """
        Encuentra la versión más reciente en una instancia.
        """
        try:
            # Buscar directorios que siguen el patrón fecha_vX
            version_dirs = []
            for d in instance_path.iterdir():
                if d.is_dir():
                    dir_name = d.name
                    # Verificar patrón como 20260201_v1
                    if '_v' in dir_name:
                        version_dirs.append((d.name, d))
            
            if not version_dirs:
                return None
            
            # Ordenar por nombre (el más reciente primero)
            version_dirs.sort(key=lambda x: x[0], reverse=True)
            return version_dirs[0][0]
            
        except Exception as e:
            print(f"   ❌ Error buscando última versión: {e}")
            return None


# Función de conveniencia para uso directo
def validate_structure(
    instance_id: str,
    version: str,
    golden_record: str
) -> Dict[str, Any]:
    """
    Función de conveniencia para validar estructura en una línea.
    
    Args:
        instance_id: ID de la instancia
        version: Versión específica
        golden_record: Ruta al CSV Golden Record
        
    Returns:
        Diccionario con resultados de validación
    """
    orchestrator = ValidationOrchestrator()
    return orchestrator.execute_validation(
        instance_id=instance_id,
        version=version,
        golden_record=golden_record
    )