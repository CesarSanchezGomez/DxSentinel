"""
Gestor de metadata persistente para árboles XML parseados.
Almacena el árbol exacto en formato serializable para acceso rápido.
"""
import json
import pickle
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import uuid

from .models.xml_elements import XMLDocument, XMLNode


class MetadataManager:
    """
    Gestor de metadata persistente.
    """
    
    def __init__(self, base_dir: Union[str, Path] = "metadata"):
        """
        Inicializa el gestor de metadata.
        
        Args:
            base_dir: Directorio base para almacenar metadata
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_instance_dir(self, instance_id: str) -> Path:
        """
        Obtiene el directorio para una instancia específica.
        
        Args:
            instance_id: ID de la instancia
            
        Returns:
            Path del directorio de la instancia
        """
        instance_dir = self.base_dir / instance_id
        instance_dir.mkdir(parents=True, exist_ok=True)
        return instance_dir
    
    def _generate_version_prefix(self, timestamp: Optional[datetime] = None) -> str:
        """
        Genera prefijo de versión basado en fecha.
        
        Args:
            timestamp: Timestamp opcional
            
        Returns:
            String con formato DDMMYY
        """
        if timestamp is None:
            timestamp = datetime.now()
        return timestamp.strftime("%d%m%y")
    
    def _get_next_version(self, instance_dir: Path, date_prefix: str) -> str:
        """
        Obtiene la siguiente versión disponible.
        
        Args:
            instance_dir: Directorio de la instancia
            date_prefix: Prefijo de fecha
            
        Returns:
            String de versión completa
        """
        existing_versions = []
        
        for item in instance_dir.iterdir():
            if item.is_dir() and item.name.startswith(date_prefix):
                existing_versions.append(item.name)
        
        if not existing_versions:
            return f"{date_prefix}_v1"
        
        # Extraer números de versión
        version_numbers = []
        for version in existing_versions:
            parts = version.split('_v')
            if len(parts) == 2 and parts[1].isdigit():
                version_numbers.append(int(parts[1]))
        
        if version_numbers:
            next_num = max(version_numbers) + 1
        else:
            next_num = 1
        
        return f"{date_prefix}_v{next_num}"
    
    def _calculate_content_hash(self, document: XMLDocument) -> str:
        """
        Calcula hash del contenido del documento para detectar cambios.
        
        Args:
            document: Documento XML
            
        Returns:
            Hash MD5 del contenido
        """
        # Serializar estructura clave para hash
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
        
        # Incluir hash de hijos
        children_hashes = [self._hash_node(child) for child in node.children]
        node_data['children_hashes'] = children_hashes
        
        node_str = json.dumps(node_data, sort_keys=True)
        return hashlib.md5(node_str.encode()).hexdigest()[:8]
    
    def save_document(self,
                     document: XMLDocument,
                     instance_id: str,
                     metadata: Optional[Dict[str, Any]] = None,
                     timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Guarda un documento en metadata.
        
        Args:
            document: Documento XML a guardar
            instance_id: ID de la instancia
            metadata: Metadata adicional a guardar
            timestamp: Timestamp opcional
            
        Returns:
            Información de la versión guardada
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Obtener directorio de instancia
        instance_dir = self._get_instance_dir(instance_id)
        
        # Generar versión
        date_prefix = self._generate_version_prefix(timestamp)
        version = self._get_next_version(instance_dir, date_prefix)
        
        # Crear directorio de versión
        version_dir = instance_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Calcular hash del contenido
        content_hash = self._calculate_content_hash(document)
        
        # Preparar metadata completa
        full_metadata = {
            'instance_id': instance_id,
            'version': version,
            'timestamp': timestamp.isoformat(),
            'content_hash': content_hash,
            'source_name': document.source_name,
            'namespaces': document.namespaces,
            'version_xml': document.version,
            'encoding': document.encoding,
            'custom_metadata': metadata or {},
            'stats': {
                'node_count': self._count_nodes(document.root),
                'unique_tags': self._collect_unique_tags(document.root)
            }
        }
        
        # Guardar metadata
        metadata_file = version_dir / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(full_metadata, f, indent=2, ensure_ascii=False)
        
        # Guardar documento serializado (usando pickle para preservar objetos Python)
        document_file = version_dir / 'document.pkl'
        with open(document_file, 'wb') as f:
            pickle.dump(document, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Guardar también en formato JSON para inspección
        json_file = version_dir / 'document.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(document.to_dict(), f, indent=2, ensure_ascii=False)
        
        return {
            'instance_id': instance_id,
            'version': version,
            'path': str(version_dir),
            'metadata_file': str(metadata_file),
            'document_file': str(document_file),
            'content_hash': content_hash,
            'timestamp': timestamp.isoformat()
        }
    
    def load_document(self,
                     instance_id: str,
                     version: Optional[str] = None) -> XMLDocument:
        """
        Carga un documento desde metadata.
        
        Args:
            instance_id: ID de la instancia
            version: Versión específica (última si None)
            
        Returns:
            Documento XML cargado
            
        Raises:
            FileNotFoundError: Si no se encuentra la metadata
        """
        instance_dir = self._get_instance_dir(instance_id)
        
        if not instance_dir.exists():
            raise FileNotFoundError(f"No metadata found for instance: {instance_id}")
        
        # Determinar versión a cargar
        if version is None:
            # Obtener última versión por timestamp
            versions = []
            for item in instance_dir.iterdir():
                if item.is_dir():
                    metadata_file = item / 'metadata.json'
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            versions.append((metadata['timestamp'], item.name))
                        except:
                            continue
            
            if not versions:
                raise FileNotFoundError(f"No valid versions found for instance: {instance_id}")
            
            # Ordenar por timestamp descendente
            versions.sort(key=lambda x: x[0], reverse=True)
            version = versions[0][1]
        
        # Cargar desde versión específica
        version_dir = instance_dir / version
        
        if not version_dir.exists():
            raise FileNotFoundError(f"Version {version} not found for instance: {instance_id}")
        
        document_file = version_dir / 'document.pkl'
        
        if not document_file.exists():
            raise FileNotFoundError(f"Document file not found: {document_file}")
        
        # Cargar documento
        with open(document_file, 'rb') as f:
            document = pickle.load(f)
        
        return document
    
    def load_metadata(self,
                     instance_id: str,
                     version: Optional[str] = None) -> Dict[str, Any]:
        """
        Carga solo metadata sin el documento completo.
        
        Args:
            instance_id: ID de la instancia
            version: Versión específica (última si None)
            
        Returns:
            Metadata cargada
        """
        instance_dir = self._get_instance_dir(instance_id)
        
        if not instance_dir.exists():
            raise FileNotFoundError(f"No metadata found for instance: {instance_id}")
        
        # Determinar versión
        if version is None:
            # Buscar última versión
            metadata_files = list(instance_dir.rglob('metadata.json'))
            if not metadata_files:
                raise FileNotFoundError(f"No metadata files found for instance: {instance_id}")
            
            # Obtener timestamps para ordenar
            versions_data = []
            for mf in metadata_files:
                try:
                    with open(mf, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    versions_data.append((metadata['timestamp'], mf))
                except:
                    continue
            
            if not versions_data:
                raise FileNotFoundError(f"No valid metadata found for instance: {instance_id}")
            
            versions_data.sort(key=lambda x: x[0], reverse=True)
            metadata_file = versions_data[0][1]
        else:
            metadata_file = instance_dir / version / 'metadata.json'
            if not metadata_file.exists():
                raise FileNotFoundError(f"Metadata not found for version: {version}")
        
        # Cargar metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return metadata
    
    def list_instances(self) -> list[str]:
        """
        Lista todas las instancias disponibles.
        
        Returns:
            Lista de IDs de instancia
        """
        instances = []
        
        if self.base_dir.exists():
            for item in self.base_dir.iterdir():
                if item.is_dir():
                    # Verificar que sea una instancia válida (tiene metadata)
                    metadata_files = list(item.rglob('metadata.json'))
                    if metadata_files:
                        instances.append(item.name)
        
        return sorted(instances)
    
    def list_versions(self, instance_id: str) -> list[Dict[str, Any]]:
        """
        Lista todas las versiones de una instancia.
        
        Args:
            instance_id: ID de la instancia
            
        Returns:
            Lista de información de versiones
        """
        instance_dir = self._get_instance_dir(instance_id)
        
        if not instance_dir.exists():
            return []
        
        versions = []
        
        for item in instance_dir.iterdir():
            if item.is_dir():
                metadata_file = item / 'metadata.json'
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # Agregar información básica
                        versions.append({
                            'version': metadata['version'],
                            'timestamp': metadata['timestamp'],
                            'content_hash': metadata['content_hash'],
                            'source_name': metadata['source_name'],
                            'path': str(item)
                        })
                    except:
                        continue
        
        # Ordenar por timestamp descendente
        versions.sort(key=lambda x: x['timestamp'], reverse=True)
        return versions
    
    def get_latest_version(self, instance_id: str) -> Optional[str]:
        """
        Obtiene la última versión de una instancia.
        
        Args:
            instance_id: ID de la instancia
            
        Returns:
            Última versión o None
        """
        versions = self.list_versions(instance_id)
        if versions:
            return versions[0]['version']
        return None
    
    def _count_nodes(self, node: XMLNode) -> int:
        """Cuenta nodos recursivamente."""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count
    
    def _collect_unique_tags(self, node: XMLNode) -> list[str]:
        """Recolecta tags únicos."""
        tags = {node.tag}
        for child in node.children:
            tags.update(self._collect_unique_tags(child))
        return sorted(tags)
    
    def cleanup_old_versions(self,
                            instance_id: str,
                            keep_last_n: int = 5) -> list[str]:
        """
        Limpia versiones antiguas, manteniendo solo las N más recientes.
        
        Args:
            instance_id: ID de la instancia
            keep_last_n: Número de versiones a mantener
            
        Returns:
            Lista de versiones eliminadas
        """
        versions = self.list_versions(instance_id)
        
        if len(versions) <= keep_last_n:
            return []
        
        # Versiones a eliminar (las más antiguas)
        to_delete = versions[keep_last_n:]
        deleted = []
        
        for version_info in to_delete:
            version_path = Path(version_info['path'])
            
            if version_path.exists():
                # Eliminar directorio recursivamente
                import shutil
                shutil.rmtree(version_path)
                deleted.append(version_info['version'])
        
        return deleted


# Singleton global para fácil acceso
_metadata_manager = None

# Singleton global para fácil acceso
_metadata_manager = None

def get_metadata_manager(base_dir: Union[str, Path] = None) -> MetadataManager:
    """
    Obtiene instancia singleton del MetadataManager.
    
    Args:
        base_dir: Directorio base para metadata.
                  Por defecto: 'backend/storage/outputs/metadata'
        
    Returns:
        Instancia de MetadataManager
    """
    global _metadata_manager
    if _metadata_manager is None:
        if base_dir is None:
            base_dir = "backend/storage/outputs/metadata"
        _metadata_manager = MetadataManager(base_dir)
    return _metadata_manager
