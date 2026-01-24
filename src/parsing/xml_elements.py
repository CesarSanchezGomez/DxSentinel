"""
Estructuras intermedias genéricas para representar nodos XML.
No asumen semántica funcional, solo capturan lo declarado.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class NodeType(str, Enum):
    """Tipos posibles de nodos, detectados por estructura no por nombre."""
    ELEMENT = "element"
    FIELD = "field"
    COMPOSITE = "composite"
    ASSOCIATION = "association"
    UNKNOWN = "unknown"

    @classmethod
    def from_structure(cls,
                       tag: str,
                       attributes: Dict[str, str],
                       children: List[XMLNode]) -> NodeType:
        """
        Determina el tipo basado en estructura, no en nombres.
        Esta es una heurística basada en patrones comunes, pero no asume nombres.
        """
        # Verificar por atributos estructurales
        if "isComposite" in attributes and attributes["isComposite"].lower() == "true":
            return cls.COMPOSITE

        if "association" in tag.lower() or "isAssociation" in attributes:
            return cls.ASSOCIATION

        # Heurística basada en contenido de hijos
        field_indicators = {"type", "label", "name", "id"}
        if any(indicator in str(attributes).lower() for indicator in field_indicators):
            return cls.FIELD

        # Default: tratar como elemento
        return cls.ELEMENT


@dataclass
class XMLNode:
    """
    Representación completa y neutra de un nodo XML.
    Captura todo lo declarado sin inferencias.
    """
    # Identificación básica
    tag: str
    technical_id: Optional[str] = None

    # Metadata completa
    attributes: Dict[str, str] = field(default_factory=dict)

    # Labels multilenguaje - conservar TODOS los idiomas
    labels: Dict[str, str] = field(default_factory=dict)  # language_code -> label

    # Jerarquía y orden
    children: List[XMLNode] = field(default_factory=list)
    parent: Optional[XMLNode] = None
    depth: int = 0
    sibling_order: int = 0

    # Metadata adicional descubierta
    namespace: Optional[str] = None
    text_content: Optional[str] = None
    node_type: NodeType = NodeType.UNKNOWN

    def __post_init__(self):
        """Validación y determinación de tipo basada en estructura."""
        # Determinar tipo basado en estructura (no en nombres esperados)
        self.node_type = NodeType.from_structure(self.tag, self.attributes, self.children)

        # Extraer technical_id de atributos si existe
        if not self.technical_id:
            possible_ids = {'id', 'technicalId', 'name', 'code'}
            for possible_id in possible_ids:
                if possible_id in self.attributes:
                    self.technical_id = self.attributes[possible_id]
                    break

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el nodo a un dict para serialización."""
        return {
            'tag': self.tag,
            'technical_id': self.technical_id,
            'attributes': self.attributes,
            'labels': self.labels,
            'node_type': self.node_type.value,
            'namespace': self.namespace,
            'text_content': self.text_content,
            'depth': self.depth,
            'sibling_order': self.sibling_order,
            'children': [child.to_dict() for child in self.children]
        }

    def find_nodes_by_tag(self, tag_pattern: str) -> List[XMLNode]:
        """Encuentra nodos por patrón de tag (sin asumir estructura)."""
        results: List[XMLNode] = []

        if tag_pattern in self.tag:
            results.append(self)

        for child in self.children:
            results.extend(child.find_nodes_by_tag(tag_pattern))

        return results

    def get_attribute(self, attr_name: str, default: Optional[str] = None) -> Optional[str]:
        """Obtiene un atributo de manera segura."""
        return self.attributes.get(attr_name, default)


@dataclass
class XMLDocument:
    """
    Documento XML completo con metadata.
    """
    root: XMLNode
    source_name: Optional[str] = None
    namespaces: Dict[str, str] = field(default_factory=dict)
    version: Optional[str] = None
    encoding: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el documento a un dict para serialización."""
        return {
            'source_name': self.source_name,
            'namespaces': self.namespaces,
            'version': self.version,
            'encoding': self.encoding,
            'root': self.root.to_dict()
        }

    def get_origin(self) -> str:
        """Obtiene el origen del nodo (sdm, csf, mixed, unknown)."""
        return self.attributes.get('data-origin', 'unknown')
    
    def is_csf_element(self) -> bool:
        """Verifica si el elemento es de CSF."""
        origin = self.get_origin()
        return origin == 'csf' or (self.technical_id and self.technical_id.endswith('_csf'))
    
    def is_sdm_element(self) -> bool:
        """Verifica si el elemento es de SDM principal."""
        origin = self.get_origin()
        return origin == 'sdm' or (self.technical_id and not self.technical_id.endswith('_csf'))
    
    def get_clean_id(self) -> str:
        """Obtiene el ID limpio (sin sufijo de origen)."""
        if not self.technical_id:
            return ''
        
        # Remover sufijos de origen
        clean_id = self.technical_id
        for suffix in ['_csf', '_sdm', '_mixed']:
            if clean_id.endswith(suffix):
                clean_id = clean_id[:-len(suffix)]
                break
        
        return clean_id
    def get_country_based_id(self, include_origin: bool = True) -> str:
        """
        Obtiene el ID basado en país según la nueva convención.
        
        Args:
            include_origin: Si True, incluye _csf/_sdm suffix
            
        Returns:
            ID en formato: [country_][cleanId]_[origin] o [country_][cleanId]
        """
        origin = self.get_origin()
        country = self.attributes.get('data-country')
        clean_id = self.get_clean_id()
        
        if not clean_id:
            return ''
        
        # Si tenemos atributo data-full-id, usarlo
        if 'data-full-id' in self.attributes:
            full_id = self.attributes['data-full-id']
            if not include_origin and full_id.endswith('_csf'):
                return full_id[:-4]  # Quitar _csf
            return full_id
        
        # Construir ID manualmente
        parts = []
        
        if country and origin == 'csf':
            parts.append(country)
        
        parts.append(clean_id)
        
        if include_origin and origin != 'sdm':
            parts.append(origin)
        
        return '_'.join(parts)
    
    def get_clean_field_id(self) -> str:
        """
        Obtiene ID limpio para campos: sin _csf suffix.
        Para CSF: MEX_homeAddress_address1
        Para SDM: homeAddress_address1
        """
        origin = self.get_origin()
        country = self.attributes.get('data-country')
        clean_id = self.get_clean_id()
        
        if not clean_id:
            return ''
        
        if country and origin == 'csf':
            return f"{country}_{clean_id}"
        
        return clean_id