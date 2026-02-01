#backend/core/parsing/orchestrator.py
"""
Orchestrator para el módulo completo de parsing XML.
Ahora con soporte para metadata persistente.
"""
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime
from .filters.xml_filter import create_hris_filter

from .loaders.xml_loader import XMLLoader
from .parsers.xml_parser import XMLParser
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
                 id: Optional[str] = None,
                 cliente: Optional[str] = None,
                 consultor: Optional[str] = None):
        """
        Inicializa el orquestador con parámetros para metadata.
        
        Args:
            element_duplication_mapping: Mapeo personalizado para duplicación
            id: ID único para la instancia de metadata
            cliente: Nombre del cliente
            consultor: Nombre del consultor
        """
        self.loader = XMLLoader()
        self.parser = XMLParser(element_duplication_mapping)
        self.normalizer = XMLNormalizer(preserve_all_data=True)
        
        # Construir metadata a partir de los parámetros
        metadata_config = {
            'id': id,
            'cliente': cliente,
            'consultor': consultor
        }
        self.metadata_manager = get_metadata_manager(**metadata_config)
    
    def parse_and_store(self,
                       xml_path: Union[str, Path],
                       id: str,
                       source_name: Optional[str] = None,
                       origin: str = 'main',
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parsea un archivo XML y lo almacena en metadata.
        
        Args:
            xml_path: Ruta al archivo XML
            id: ID para metadata
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
            id=id,
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
                            id: str,
                            csf_xml_paths: Optional[List[Union[str, Path]]] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parsea, fusiona y almacena múltiples archivos XML.
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
                # APLICAR FILTRO HRIS
                filter_instance = create_hris_filter(filter_csf=False)
                document = filter_instance.filter_document(document, 'main')
            
            documents.append(document)
        
        # Fusionar si hay múltiples documentos
        if len(documents) > 1:
            fused_document = _fuse_csf_with_main(documents)
        else:
            fused_document = documents[0]
        
        # Normalizar para respuesta inmediata
        normalized = normalizer.normalize_document(fused_document)
        
        # Almacenar en metadata
        storage_info = self.metadata_manager.save_document(
            document=fused_document,
            id=id,
            metadata={
                'main_xml_path': str(main_xml_path),
                'csf_xml_paths': [str(p) for p in (csf_xml_paths or [])],
                'file_count': len(files),
                'filter_applied': 'hris-only',  # Registrar que se aplicó filtro
                **(metadata or {})
            }
        )
        
        return {
            'storage': storage_info,
            'normalized': normalized
        }
    
    def parse_and_store(self,
                       xml_path: Union[str, Path],
                       id: str,
                       source_name: Optional[str] = None,
                       origin: str = 'main',
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parsea un archivo XML y lo almacena en metadata.
        """
        # Cargar y parsear XML
        root = self.loader.load_from_file(xml_path, source_name)
        document = self.parser.parse_document(root, source_name)
        
        # Marcar origen
        if origin != 'main':
            _mark_nodes_origin(document.root, origin)
        
        # APLICAR FILTRO HRIS solo para documentos main
        if origin == 'main':
            filter_instance = create_hris_filter(filter_csf=False)
            document = filter_instance.filter_document(document, 'main')
        
        # Normalizar para respuesta inmediata
        normalized = self.normalizer.normalize_document(document)
        
        # Almacenar en metadata
        storage_info = self.metadata_manager.save_document(
            document=document,
            id=id,
            metadata={
                'xml_path': str(xml_path),
                'source_name': source_name,
                'origin': origin,
                'filter_applied': 'hris-only' if origin == 'main' else 'none',
                **(metadata or {})
            }
        )
        
        return {
            'storage': storage_info,
            'normalized': normalized
        }
    
    def load_from_metadata(self,
                          id: str,
                          version: Optional[str] = None,
                          normalize: bool = True) -> Dict[str, Any]:
        """
        Carga un documento desde metadata.
        
        Args:
            id: ID de la instancia
            version: Versión específica (última si None)
            normalize: Si se debe normalizar el documento cargado
            
        Returns:
            Documento cargado (normalizado o XMLDocument)
        """
        # Cargar documento desde metadata
        document = self.metadata_manager.load_document(id, version)
        
        if normalize:
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
                         id: str,
                         version: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene información de metadata sin cargar el documento completo.
        
        Args:
            id: ID de la instancia
            version: Versión específica (última si None)
            
        Returns:
            Información de metadata
        """
        return self.metadata_manager.load_metadata(id, version)
    
    # Funciones existentes (compatibilidad hacia atrás)
    def parse_single_file(self, 
                         xml_path: Union[str, Path],
                         source_name: Optional[str] = None,
                         origin: str = 'main') -> Dict[str, Any]:
        root = self.loader.load_from_file(xml_path, source_name)
        document = self.parser.parse_document(root, source_name)
        
        if origin != 'main':
            _mark_nodes_origin(document.root, origin)
        
        return self.normalizer.normalize_document(document)


def create_orchestrator(element_duplication_mapping: Optional[Dict] = None,
                       id: Optional[str] = None,
                       cliente: Optional[str] = None,
                       consultor: Optional[str] = None) -> XMLParsingOrchestrator:
    """
    Crea y retorna un orquestador configurado.
    
    Args:
        element_duplication_mapping: Mapeo personalizado para duplicación
        id: ID único para la instancia de metadata
        cliente: Nombre del cliente
        consultor: Nombre del consultor
    """
    return XMLParsingOrchestrator(
        element_duplication_mapping=element_duplication_mapping,
        id=id,
        cliente=cliente,
        consultor=consultor
    )


def parse_and_store_xml(main_xml_path: Union[str, Path],
                       id: str,
                       csf_xml_path: Optional[Union[str, Path]] = None,
                       element_duplication_mapping: Optional[Dict] = None,
                       metadata: Optional[Dict[str, Any]] = None,
                       cliente: Optional[str] = None,
                       consultor: Optional[str] = None) -> Dict[str, Any]:
    """
    Pipeline completo con almacenamiento en metadata.
    
    Args:
        main_xml_path: Ruta al archivo XML principal
        id: ID único para metadata
        csf_xml_path: Ruta(s) a archivos CSF
        element_duplication_mapping: Mapeo para duplicación
        metadata: Metadata adicional
        cliente: Nombre del cliente
        consultor: Nombre del consultor
        
    Returns:
        Dict con 'storage' (info metadata) y 'normalized' (modelo)
    """
    orchestrator = create_orchestrator(
        element_duplication_mapping=element_duplication_mapping,
        id=id,
        cliente=cliente,
        consultor=consultor
    )
    
    if csf_xml_path:
        csf_paths = [csf_xml_path] if not isinstance(csf_xml_path, list) else csf_xml_path
        return orchestrator.parse_fuse_and_store(
            main_xml_path=main_xml_path,
            id=id,
            csf_xml_paths=csf_paths,
            metadata=metadata
        )
    else:
        return orchestrator.parse_and_store(
            xml_path=main_xml_path,
            id=id,
            source_name='SDM_Principal',
            origin='main',
            metadata=metadata
        )


def load_from_metadata(id: str,
                      version: Optional[str] = None,
                      normalize: bool = True,
                      cliente: Optional[str] = None,
                      consultor: Optional[str] = None) -> Dict[str, Any]:
    """
    Carga desde metadata.
    
    Args:
        id: ID de la instancia
        version: Versión específica
        normalize: Si se debe normalizar
        cliente: Nombre del cliente
        consultor: Nombre del consultor
        
    Returns:
        Documento cargado
    """
    orchestrator = create_orchestrator(
        id=id,
        cliente=cliente,
        consultor=consultor
    )
    return orchestrator.load_from_metadata(id, version, normalize)