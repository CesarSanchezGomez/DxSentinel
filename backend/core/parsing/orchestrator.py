"""
Orchestrator para el módulo completo de parsing XML.
Ahora con soporte para metadata persistente.
"""
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime

from .loaders.xml_loader import XMLLoader
from .parsers.xml_parser import XMLParser, parse_multiple_xml_files
from .normalizers.xml_normalizer import XMLNormalizer
from .models.xml_elements import XMLDocument
from .utils.xml_merger import _mark_nodes_origin, _fuse_csf_with_main
from .metadata_manager import get_metadata_manager


class XMLParsingOrchestrator:
    """
    Orquestador que maneja todo el flujo de parsing XML.
    """
    
    def __init__(self, 
                 element_duplication_mapping: Optional[Dict] = None,
                 metadata_dir: Union[str, Path] = "metadata"):
        """
        Inicializa el orquestador.
        
        Args:
            element_duplication_mapping: Mapeo personalizado para duplicación
            metadata_dir: Directorio para almacenar metadata
        """
        self.loader = XMLLoader()
        self.parser = XMLParser(element_duplication_mapping)
        self.normalizer = XMLNormalizer(preserve_all_data=True)
        self.metadata_manager = get_metadata_manager(metadata_dir)
    
    def parse_and_store(self,
                       xml_path: Union[str, Path],
                       instance_id: str,
                       source_name: Optional[str] = None,
                       origin: str = 'main',
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parsea un archivo XML y lo almacena en metadata.
        
        Args:
            xml_path: Ruta al archivo XML
            instance_id: ID de la instancia para metadata
            source_name: Nombre identificador del origen
            origin: Origen de los datos
            metadata: Metadata adicional a almacenar
            
        Returns:
            Diccionario con información de almacenamiento y modelo normalizado
        """
        # Cargar y parsear XML
        root = self.loader.load_from_file(xml_path, source_name)
        document = self.parser.parse_document(root, source_name)
        
        # Marcar origen
        if origin != 'main':
            _mark_nodes_origin(document.root, origin)
        
        # Normalizar para respuesta inmediata
        normalized = self.normalizer.normalize_document(document)
        
        # Almacenar en metadata
        storage_info = self.metadata_manager.save_document(
            document=document,
            instance_id=instance_id,
            metadata={
                'xml_path': str(xml_path),
                'source_name': source_name,
                'origin': origin,
                **(metadata or {})
            }
        )
        
        return {
            'storage': storage_info,
            'normalized': normalized
        }
    
    def parse_fuse_and_store(self,
                            main_xml_path: Union[str, Path],
                            instance_id: str,
                            csf_xml_paths: Optional[List[Union[str, Path]]] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parsea, fusiona y almacena múltiples archivos XML.
        
        Args:
            main_xml_path: Ruta al archivo principal
            instance_id: ID de la instancia
            csf_xml_paths: Lista de rutas a archivos CSF
            metadata: Metadata adicional
            
        Returns:
            Diccionario con información de almacenamiento y modelo normalizado
        """
        # Preparar lista de archivos
        files = [{
            'path': str(main_xml_path),
            'type': 'main',
            'source_name': 'SDM_Principal'
        }]
        
        if csf_xml_paths:
            for i, csf_path in enumerate(csf_xml_paths):
                files.append({
                    'path': str(csf_path),
                    'type': 'csf',
                    'source_name': f'CSF_SDM_{i}'
                })
        
        # Parsear múltiples archivos
        loader = XMLLoader()
        parser = XMLParser()
        normalizer = XMLNormalizer()
        
        documents = []
        for file_info in files:
            xml_root = loader.load_from_file(file_info['path'], file_info['source_name'])
            document = parser.parse_document(xml_root, file_info['source_name'])
            document.file_type = file_info['type']
            
            if file_info['type'] == 'main':
                _mark_nodes_origin(document.root, 'sdm')
            
            documents.append(document)
        
        # Fusionar si hay múltiples documentos
        if len(documents) > 1:
            from .utils.xml_merger import _fuse_csf_with_main
            fused_document = _fuse_csf_with_main(documents)
        else:
            fused_document = documents[0]
        
        # Normalizar para respuesta inmediata
        normalized = normalizer.normalize_document(fused_document)
        
        # Almacenar en metadata
        storage_info = self.metadata_manager.save_document(
            document=fused_document,
            instance_id=instance_id,
            metadata={
                'main_xml_path': str(main_xml_path),
                'csf_xml_paths': [str(p) for p in (csf_xml_paths or [])],
                'file_count': len(files),
                **(metadata or {})
            }
        )
        
        return {
            'storage': storage_info,
            'normalized': normalized
        }
    
    def load_from_metadata(self,
                          instance_id: str,
                          version: Optional[str] = None,
                          normalize: bool = True) -> Dict[str, Any]:
        """
        Carga un documento desde metadata.
        
        Args:
            instance_id: ID de la instancia
            version: Versión específica (última si None)
            normalize: Si se debe normalizar el documento cargado
            
        Returns:
            Documento cargado (normalizado o XMLDocument)
        """
        # Cargar documento desde metadata
        document = self.metadata_manager.load_document(instance_id, version)
        
        if normalize:
            # Normalizar para consistencia con otras funciones
            normalized = self.normalizer.normalize_document(document)
            return {
                'document': document,
                'normalized': normalized
            }
        else:
            return {
                'document': document
            }
    
    def get_metadata_info(self,
                         instance_id: str,
                         version: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene información de metadata sin cargar el documento completo.
        
        Args:
            instance_id: ID de la instancia
            version: Versión específica (última si None)
            
        Returns:
            Información de metadata
        """
        return self.metadata_manager.load_metadata(instance_id, version)
    
    # Funciones existentes (compatibilidad hacia atrás)
    def parse_single_file(self, 
                         xml_path: Union[str, Path],
                         source_name: Optional[str] = None,
                         origin: str = 'main') -> Dict[str, Any]:
        """Mantener para compatibilidad."""
        root = self.loader.load_from_file(xml_path, source_name)
        document = self.parser.parse_document(root, source_name)
        
        if origin != 'main':
            _mark_nodes_origin(document.root, origin)
        
        return self.normalizer.normalize_document(document)
    
    def parse_and_fuse_files(self,
                            main_xml_path: Union[str, Path],
                            csf_xml_paths: Optional[List[Union[str, Path]]] = None) -> Dict[str, Any]:
        """Mantener para compatibilidad."""
        files = [{'path': str(main_xml_path), 'type': 'main', 'source_name': 'SDM_Principal'}]
        
        if csf_xml_paths:
            for i, csf_path in enumerate(csf_xml_paths):
                files.append({
                    'path': str(csf_path),
                    'type': 'csf',
                    'source_name': f'CSF_SDM_{i}'
                })
        
        return parse_multiple_xml_files(files)


# Función de conveniencia mejorada
def create_orchestrator(element_duplication_mapping: Optional[Dict] = None,
                       metadata_dir: Union[str, Path] = "metadata") -> XMLParsingOrchestrator:
    """
    Crea y retorna un orquestador configurado.
    """
    return XMLParsingOrchestrator(element_duplication_mapping, metadata_dir)


# Función principal simplificada con metadata
def parse_and_store_xml(main_xml_path: Union[str, Path],
                       instance_id: str,
                       csf_xml_path: Optional[Union[str, Path]] = None,
                       element_duplication_mapping: Optional[Dict] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Pipeline completo con almacenamiento en metadata.
    
    Returns:
        Dict con 'storage' (info metadata) y 'normalized' (modelo)
    """
    orchestrator = create_orchestrator(element_duplication_mapping)
    
    if csf_xml_path:
        csf_paths = [csf_xml_path] if not isinstance(csf_xml_path, list) else csf_xml_path
        return orchestrator.parse_fuse_and_store(
            main_xml_path=main_xml_path,
            instance_id=instance_id,
            csf_xml_paths=csf_paths,
            metadata=metadata
        )
    else:
        return orchestrator.parse_and_store(
            xml_path=main_xml_path,
            instance_id=instance_id,
            source_name='SDM_Principal',
            origin='main',
            metadata=metadata
        )


# Función para carga desde metadata
def load_from_metadata(instance_id: str,
                      version: Optional[str] = None,
                      normalize: bool = True,
                      metadata_dir: Union[str, Path] = "metadata") -> Dict[str, Any]:
    """
    Carga desde metadata.
    
    Args:
        instance_id: ID de la instancia
        version: Versión específica
        normalize: Si se debe normalizar
        metadata_dir: Directorio de metadata
        
    Returns:
        Documento cargado
    """
    orchestrator = create_orchestrator(metadata_dir=metadata_dir)
    return orchestrator.load_from_metadata(instance_id, version, normalize)