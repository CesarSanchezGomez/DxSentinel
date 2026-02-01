# backend/core/parsing/filters/xml_filter.py
"""
Filtro para elementos XML basado en reglas específicas.
Mantiene la estructura del árbol intacta mientras filtra nodos.
"""
import re
from typing import Any, Optional, List, Set

from realtime import Dict
from ..models.xml_elements import XMLNode, XMLDocument


class XMLFilter:
    """
    Filtra elementos XML manteniendo estructura.
    """
    
    # Patrones para identificar elementos HRIS
    HRIS_ELEMENT_PATTERNS = [
        r'^hris-.*',                    # hris-element, hris-action, etc.
        r'.*hris.*element.*',           # cualquier cosa con "hris" y "element"
        r'.*hris.*action.*',            # cualquier cosa con "hris" y "action"
    ]
    
    # Patrones para identificar elementos a preservar incluso si no son HRIS
    # (nodos contenedores que pueden tener hijos HRIS)
    PRESERVE_STRUCTURE_PATTERNS = [
        r'^succession-data-model$',     # elemento raíz
        r'^standard-element$',          # contenedores potenciales
        r'^custom-filters$',
        r'^element-permission$',
        r'^dg-filters$',
    ]
    
    def __init__(self, filter_csf: bool = False):
        """
        Args:
            filter_csf: Si es True, aplica filtro también a documentos CSF
        """
        self.filter_csf = filter_csf
        self._compiled_hris_patterns = [re.compile(p, re.IGNORECASE) 
                                       for p in self.HRIS_ELEMENT_PATTERNS]
        self._compiled_structure_patterns = [re.compile(p, re.IGNORECASE) 
                                           for p in self.PRESERVE_STRUCTURE_PATTERNS]
    
    def filter_document(self, document: XMLDocument, file_type: str = 'main') -> XMLDocument:
        """
        Aplica filtro al documento completo.
        
        Args:
            document: Documento XML a filtrar
            file_type: Tipo de archivo ('main' o 'csf')
            
        Returns:
            Documento filtrado (nueva instancia para inmutabilidad)
        """
        # No filtrar documentos CSF a menos que se especifique
        if file_type == 'csf' and not self.filter_csf:
            return document
        
        # Crear copia profunda filtrada
        filtered_root = self._filter_node(document.root)
        
        # Crear nuevo documento con metadata original
        filtered_doc = XMLDocument(
            root=filtered_root,
            source_name=document.source_name,
            namespaces=document.namespaces.copy(),
            version=document.version,
            encoding=document.encoding
        )
        
        return filtered_doc
    
    def _filter_node(self, node: Optional[XMLNode]) -> Optional[XMLNode]:
        """
        Filtra nodo recursivamente manteniendo estructura.
        """
        if node is None:
            return None
        
        # 1. Si el nodo es HRIS, mantenerlo completo
        if self._is_hris_element(node):
            # Filtrar hijos recursivamente
            filtered_children = []
            for child in node.children:
                filtered_child = self._filter_node(child)
                if filtered_child:
                    filtered_children.append(filtered_child)
            
            # Crear copia con hijos filtrados
            filtered_node = self._create_filtered_copy(node, filtered_children)
            return filtered_node
        
        # 2. Si el nodo es necesario para preservar estructura, mantenerlo
        if self._should_preserve_structure(node):
            # Filtrar hijos recursivamente
            filtered_children = []
            for child in node.children:
                filtered_child = self._filter_node(child)
                if filtered_child:
                    filtered_children.append(filtered_child)
            
            # Si tiene hijos después del filtrado, mantener nodo
            if filtered_children:
                filtered_node = self._create_filtered_copy(node, filtered_children)
                return filtered_node
        
        # 3. Para otros nodos, verificar si tienen descendientes HRIS
        hris_descendants = self._collect_hris_descendants(node)
        if hris_descendants:
            # Mantener nodo con estructura mínima
            filtered_children = []
            for child in node.children:
                filtered_child = self._filter_node(child)
                if filtered_child:
                    filtered_children.append(filtered_child)
            
            if filtered_children:
                filtered_node = self._create_filtered_copy(node, filtered_children)
                return filtered_node
        
        # 4. Nodo no tiene descendientes HRIS, eliminarlo
        return None
    
    def _is_hris_element(self, node: XMLNode) -> bool:
        """Determina si un elemento es HRIS basado en su tag."""
        tag_lower = node.tag.lower()
        
        # Verificar patrones HRIS
        for pattern in self._compiled_hris_patterns:
            if pattern.match(tag_lower):
                return True
        
        # Verificar atributos específicos
        if 'hris' in tag_lower:
            return True
        
        # Verificar si tiene atributo que indique HRIS
        hris_indicators = {'hris-type', 'hris-category', 'is-hris'}
        if any(indicator in node.attributes for indicator in hris_indicators):
            return True
        
        return False
    
    def _should_preserve_structure(self, node: XMLNode) -> bool:
        """Determina si un nodo debe preservarse por estructura."""
        tag_lower = node.tag.lower()
        
        for pattern in self._compiled_structure_patterns:
            if pattern.match(tag_lower):
                return True
        
        return False
    
    def _collect_hris_descendants(self, node: XMLNode) -> List[XMLNode]:
        """Recolecta todos los descendientes HRIS de un nodo."""
        hris_nodes = []
        
        if self._is_hris_element(node):
            hris_nodes.append(node)
        
        for child in node.children:
            hris_nodes.extend(self._collect_hris_descendants(child))
        
        return hris_nodes
    
    def _create_filtered_copy(self, original: XMLNode, 
                            filtered_children: List[XMLNode]) -> XMLNode:
        """Crea una copia filtrada del nodo manteniendo metadata."""
        # Crear nuevo nodo con misma metadata
        filtered_node = XMLNode(
            tag=original.tag,
            technical_id=original.technical_id,
            attributes=original.attributes.copy(),
            labels=original.labels.copy(),
            children=filtered_children,
            parent=None,  # Se establecerá después
            depth=original.depth,
            sibling_order=original.sibling_order,
            namespace=original.namespace,
            text_content=original.text_content,
            node_type=original.node_type
        )
        
        # Establecer parent en hijos
        for child in filtered_children:
            child.parent = filtered_node
        
        return filtered_node
    
    def get_filter_statistics(self, document: XMLDocument) -> Dict[str, Any]:
        """Obtiene estadísticas del filtro aplicado."""
        original_count = self._count_nodes(document.root)
        filtered_root = self._filter_node(document.root)
        filtered_count = self._count_nodes(filtered_root) if filtered_root else 0
        
        hris_nodes = self._collect_hris_descendants(document.root)
        hris_tags = {node.tag for node in hris_nodes}
        
        return {
            'original_node_count': original_count,
            'filtered_node_count': filtered_count,
            'nodes_removed': original_count - filtered_count,
            'hris_nodes_found': len(hris_nodes),
            'unique_hris_tags': sorted(hris_tags)
        }
    
    def _count_nodes(self, node: Optional[XMLNode]) -> int:
        """Cuenta nodos recursivamente."""
        if node is None:
            return 0
        
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        
        return count


def create_hris_filter(filter_csf: bool = False) -> XMLFilter:
    """
    Factory function para crear filtro HRIS.
    
    Args:
        filter_csf: Si se debe aplicar filtro a documentos CSF
        
    Returns:
        Instancia de XMLFilter configurada
    """
    return XMLFilter(filter_csf=filter_csf)