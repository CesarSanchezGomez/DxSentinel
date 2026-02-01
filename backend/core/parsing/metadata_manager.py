#/backend/core/parsing/metadata_manager.py
"""
Gestor de metadata persistente para árboles XML parseados.
Almacena el árbol exacto en formato serializable para acceso rápido.
"""
import json
import pickle
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

from .models.xml_elements import XMLDocument, XMLNode


class MetadataManager:
    """
    Gestor de metadata persistente.
    """
    
    def __init__(self, 
                 id: Optional[str] = None,
                 cliente: Optional[str] = None,
                 consultor: Optional[str] = None):
        """
        Inicializa el gestor de metadata.
        
        Args:
            id: ID único para la instancia
            cliente: Nombre del cliente
            consultor: Nombre del consultor
        """
        # Usar valores por defecto si no se proporcionan
        self.id = id or "default_id"
        self.cliente = cliente or "default_cliente"
        self.consultor = consultor or "default_consultor"
        
        # Obtener fecha actual
        fecha_actual = datetime.now().strftime("%Y%m%d")
        
        # Generar versión automáticamente según las existentes
        version = self._get_next_version(self.id, fecha_actual)
        
        # Estructura: /metadata/[id]/[fecha]_[version]/
        self.base_dir = Path("backend/storage/metadata") / self.id / f"{fecha_actual}_{version}"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Parámetros del sistema para incluir en metadata
        self.metadata_params = {
            'id': self.id,
            'cliente': self.cliente,
            'consultor': self.consultor,
            'fecha_creacion': datetime.now().isoformat(),
            'estructura_creacion': f"/metadata/{self.id}/{fecha_actual}_{version}/"
        }
    
    def _get_next_version(self, id: str, fecha: str) -> str:
        """
        Calcula la siguiente versión disponible para la fecha actual.
        
        Args:
            id: ID único
            fecha: Fecha en formato YYYYMMDD
            
        Returns:
            String de versión (v1, v2, etc.)
        """
        base_path = Path("backend/storage/metadata") / id
        
        if not base_path.exists():
            return "v1"
        
        # Buscar versiones existentes para esta fecha
        existing_versions = []
        for item in base_path.iterdir():
            if item.is_dir() and item.name.startswith(fecha):
                try:
                    # Extraer versión del nombre: fecha_version
                    version_part = item.name.split('_')[1]
                    if version_part.startswith('v'):
                        version_num = int(version_part[1:])
                        existing_versions.append(version_num)
                except (IndexError, ValueError):
                    continue
        
        if not existing_versions:
            return "v1"
        
        next_version = max(existing_versions) + 1
        return f"v{next_version}"
    
    def _calculate_content_hash(self, document: XMLDocument) -> str:
        """
        Calcula hash del contenido del documento.
        
        Args:
            document: Documento XML
            
        Returns:
            Hash MD5 del contenido
        """
        content_data = {
            'source_name': document.source_name,
            'namespaces': document.namespaces,
            'root_hash': self._hash_node(document.root)
        }
        
        content_str = json.dumps(content_data, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()[:12]
    
    def _hash_node(self, node: XMLNode) -> str:
        """
        Calcula hash recursivo de un nodo.
        
        Args:
            node: Nodo XML
            
        Returns:
            Hash del nodo y sus hijos
        """
        node_data = {
            'tag': node.tag,
            'technical_id': node.technical_id,
            'attributes': node.attributes,
            'labels': node.labels,
            'node_type': node.node_type.value,
            'text_content': node.text_content,
            'children_count': len(node.children)
        }
        
        children_hashes = [self._hash_node(child) for child in node.children]
        node_data['children_hashes'] = children_hashes
        
        node_str = json.dumps(node_data, sort_keys=True)
        return hashlib.md5(node_str.encode()).hexdigest()[:8]
    
    def save_document(self,
                     document: XMLDocument,
                     id: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Guarda un documento en metadata.
        
        Args:
            document: Documento XML a guardar
            id: ID de la instancia (usa el del manager si no se proporciona)
            metadata: Metadata adicional a guardar
            
        Returns:
            Información de la versión guardada
        """
        # Usar ID proporcionado o el del manager
        document_id = id or self.id
        
        timestamp = datetime.now()
        
        # Calcular hash del contenido
        content_hash = self._calculate_content_hash(document)
        
        # Preparar metadata completa con información de creación
        full_metadata = {
            # Información de creación del sistema (como comentarios en la estructura)
            'system_info': {
                'created_by': 'MetadataManager',
                'creation_timestamp': datetime.now().isoformat(),
                'parameters': {
                    'id': self.id,
                    'cliente': self.cliente,
                    'consultor': self.consultor
                },
                'directory_structure': f"/metadata/{self.id}/{self.base_dir.name}/"
            },
            
            # Metadata del documento
            'document_info': {
                'id': document_id,
                'timestamp': timestamp.isoformat(),
                'content_hash': content_hash,
                'source_name': document.source_name,
                'namespaces': document.namespaces,
                'version_xml': document.version,
                'encoding': document.encoding,
                'stats': {
                    'node_count': self._count_nodes(document.root),
                    'unique_tags': self._collect_unique_tags(document.root)
                }
            },
            
            # Metadata personalizada
            'custom_metadata': metadata or {}
        }
        
        # Guardar metadata
        metadata_file = self.base_dir / f"metadata_{document_id}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(full_metadata, f, indent=2, ensure_ascii=False)
        
        # Guardar documento serializado
        document_file = self.base_dir / f"document_{document_id}.pkl"
        with open(document_file, 'wb') as f:
            pickle.dump(document, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Guardar en formato JSON para inspección
        json_file = self.base_dir / f"document_{document_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(document.to_dict(), f, indent=2, ensure_ascii=False)
        
        return {
            'id': document_id,
            'path': str(self.base_dir),
            'metadata_file': str(metadata_file),
            'document_file': str(document_file),
            'json_file': str(json_file),
            'content_hash': content_hash,
            'timestamp': timestamp.isoformat()
        }
    
    def load_document(self,
                     id: str,
                     version: Optional[str] = None) -> XMLDocument:
        """
        Carga un documento desde metadata.
        
        Args:
            id: ID de la instancia
            version: Versión específica (última si None)
            
        Returns:
            Documento XML cargado
            
        Raises:
            FileNotFoundError: Si no se encuentra la metadata
        """
        # Determinar directorio de búsqueda
        if version:
            # Buscar versión específica
            version_dir = Path("backend/storage/metadata") / id / version
        else:
            # Buscar última versión
            base_path = Path("backend/storage/metadata") / id
            if not base_path.exists():
                raise FileNotFoundError(f"No metadata found for id: {id}")
            
            # Obtener directorios ordenados por nombre (fecha descendente)
            dirs = sorted([d for d in base_path.iterdir() if d.is_dir()], 
                         key=lambda x: x.name, reverse=True)
            
            if not dirs:
                raise FileNotFoundError(f"No versions found for id: {id}")
            
            version_dir = dirs[0]
        
        # Buscar documento
        document_file = version_dir / f"document_{id}.pkl"
        
        if not document_file.exists():
            # Intentar con patrón alternativo
            document_files = list(version_dir.glob("*.pkl"))
            if not document_files:
                raise FileNotFoundError(f"No document file found in: {version_dir}")
            document_file = document_files[0]
        
        # Cargar documento
        with open(document_file, 'rb') as f:
            document = pickle.load(f)
        
        return document
    
    def load_metadata(self,
                     id: str,
                     version: Optional[str] = None) -> Dict[str, Any]:
        """
        Carga solo metadata sin el documento completo.
        
        Args:
            id: ID de la instancia
            version: Versión específica (última si None)
            
        Returns:
            Metadata cargada
        """
        # Determinar directorio
        if version:
            version_dir = Path("backend/storage/metadata") / id / version
        else:
            base_path = Path("backend/storage/metadata") / id
            if not base_path.exists():
                raise FileNotFoundError(f"No metadata found for id: {id}")
            
            dirs = sorted([d for d in base_path.iterdir() if d.is_dir()], 
                         key=lambda x: x.name, reverse=True)
            
            if not dirs:
                raise FileNotFoundError(f"No versions found for id: {id}")
            
            version_dir = dirs[0]
        
        # Buscar archivo de metadata
        metadata_file = version_dir / f"metadata_{id}.json"
        
        if not metadata_file.exists():
            # Intentar con patrón alternativo
            metadata_files = list(version_dir.glob("metadata*.json"))
            if not metadata_files:
                raise FileNotFoundError(f"No metadata file found in: {version_dir}")
            metadata_file = metadata_files[0]
        
        # Cargar metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return metadata
    
    def list_versions(self, id: str) -> List[Dict[str, Any]]:
        """
        Lista todas las versiones de un ID.
        
        Args:
            id: ID de la instancia
            
        Returns:
            Lista de información de versiones
        """
        base_path = Path("backend/storage/metadata") / id
        
        if not base_path.exists():
            return []
        
        versions = []
        
        for item in base_path.iterdir():
            if item.is_dir():
                # Buscar archivos de metadata
                metadata_files = list(item.glob("metadata*.json"))
                if metadata_files:
                    try:
                        metadata_file = metadata_files[0]
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        versions.append({
                            'version': item.name,
                            'timestamp': metadata.get('document_info', {}).get('timestamp', ''),
                            'content_hash': metadata.get('document_info', {}).get('content_hash', ''),
                            'source_name': metadata.get('document_info', {}).get('source_name', ''),
                            'path': str(item)
                        })
                    except:
                        continue
        
        # Ordenar por versión (nombre de directorio) descendente
        versions.sort(key=lambda x: x['version'], reverse=True)
        return versions
    
    def _count_nodes(self, node: XMLNode) -> int:
        """Cuenta nodos recursivamente."""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count
    
    def _collect_unique_tags(self, node: XMLNode) -> List[str]:
        """Recolecta tags únicos."""
        tags = {node.tag}
        for child in node.children:
            tags.update(self._collect_unique_tags(child))
        return sorted(tags)


def get_metadata_manager(id: Optional[str] = None,
                        cliente: Optional[str] = None,
                        consultor: Optional[str] = None) -> MetadataManager:
    """
    Crea y retorna una instancia de MetadataManager.
    
    Args:
        id: ID único para la instancia
        cliente: Nombre del cliente
        consultor: Nombre del consultor
        
    Returns:
        Instancia de MetadataManager
    """
    return MetadataManager(
        id=id,
        cliente=cliente,
        consultor=consultor
    )