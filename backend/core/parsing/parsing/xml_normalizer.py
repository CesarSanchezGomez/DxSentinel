from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import re

from .xml_elements import XMLNode, XMLDocument


class XMLNormalizer:
    """
    Normalizador que conserva toda la metadata.
    """

    BOOLEAN_PATTERNS = {
        'true': True,
        'false': False,
        'yes': True,
        'no': False,
        '1': True,
        '0': False
    }

    NUMBER_PATTERN = re.compile(r'^-?\d+(\.\d+)?$')
    ISO_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$')

    def __init__(self, preserve_all_data: bool = True):
        self.preserve_all_data = preserve_all_data

    def normalize_document(self, document: XMLDocument) -> Dict[str, Any]:
        """
        Normaliza un documento completo a un formato estructurado.
        """
        normalized = {
            'metadata': self._normalize_document_metadata(document),
            'structure': self._normalize_node(document.root),
            'statistics': self._calculate_statistics(document)
        }

        return normalized

    def _normalize_document_metadata(self, document: XMLDocument) -> Dict[str, Any]:
        """Normaliza metadata del documento."""
        return {
            'source': document.source_name,
            'namespaces': document.namespaces,
            'version': document.version,
            'encoding': document.encoding,
            'parsed_at': datetime.utcnow().isoformat() + 'Z'
        }

    def _normalize_node(self, node: XMLNode) -> Dict[str, Any]:
        """
        Normaliza un nodo recursivamente.
        """
        normalized = {
            'tag': node.tag,
            'node_type': node.node_type.value,
            'technical_id': node.technical_id,
            'depth': node.depth,
            'sibling_order': node.sibling_order,
            'namespace': node.namespace,
            'text_content': node.text_content,
            'attributes': {
                'raw': node.attributes,
                'normalized': self._normalize_attributes(node.attributes)
            },
            'labels': node.labels,
            'children': [self._normalize_node(child) for child in node.children],
            'has_children': len(node.children) > 0,
            'has_labels': len(node.labels) > 0,
            'has_attributes': len(node.attributes) > 0
        }

        return normalized

    def _normalize_attributes(self, attributes: Dict[str, str]) -> Dict[str, Any]:
        """
        Normaliza atributos cuando el tipo es inequívoco.
        """
        normalized = {}

        for key, value in attributes.items():
            if value is None:
                normalized[key] = None
                continue

            normalized_value = self._normalize_value(value)

            if normalized_value != value and self._is_normalization_reliable(value):
                normalized[key] = {
                    'raw': value,
                    'normalized': normalized_value,
                    'inferred_type': type(normalized_value).__name__
                }
            else:
                normalized[key] = value

        return normalized

    def _normalize_value(self, value: str) -> Any:
        """
        Normaliza un valor string a tipo más específico cuando es inequívoco.
        """
        value_str = str(value).strip()
        lower_val = value_str.lower()

        if lower_val in self.BOOLEAN_PATTERNS:
            return self.BOOLEAN_PATTERNS[lower_val]

        if value_str.isdigit() or (value_str.startswith('-') and value_str[1:].isdigit()):
            try:
                int_val = int(value_str)
                if str(int_val) == value_str:
                    return int_val
            except (ValueError, OverflowError):
                pass

        if self.NUMBER_PATTERN.match(value_str):
            try:
                float_val = float(value_str)
                if '.' in value_str:
                    return float_val
                elif float_val.is_integer():
                    return int(float_val)
            except (ValueError, OverflowError):
                pass

        if self.ISO_DATE_PATTERN.match(value_str):
            try:
                from datetime import datetime
                if 'T' in value_str:
                    dt = datetime.fromisoformat(value_str.replace('Z', '+00:00'))
                    return dt.isoformat()
                else:
                    return value_str
            except (ValueError, TypeError):
                pass

        return value

    def _is_normalization_reliable(self, value: str) -> bool:
        """
        Determina si la normalización de tipo es confiable.
        """
        value_str = str(value).strip()

        if value_str.lower() in self.BOOLEAN_PATTERNS:
            return True

        if value_str.isdigit():
            try:
                return str(int(value_str)) == value_str
            except (ValueError, OverflowError):
                return False

        if self.NUMBER_PATTERN.match(value_str):
            try:
                float_val = float(value_str)
                return str(float_val) == value_str or f"{float_val:.{len(value_str.split('.')[1])}f}" == value_str
            except (ValueError, OverflowError, IndexError):
                return False

        if self.ISO_DATE_PATTERN.match(value_str):
            return True

        return False

    def _calculate_statistics(self, document: XMLDocument) -> Dict[str, Any]:
        """Calcula estadísticas del documento normalizado."""
        stats = {
            'total_nodes': self._count_nodes(document.root),
            'unique_tags': self._collect_unique_tags(document.root),
            'attribute_summary': self._summarize_attributes(document.root),
            'label_summary': self._summarize_labels(document.root)
        }

        return stats

    def _count_nodes(self, node: XMLNode) -> int:
        """Cuenta el total de nodos."""
        count = 1

        for child in node.children:
            count += self._count_nodes(child)

        return count

    def _collect_unique_tags(self, node: XMLNode) -> List[str]:
        """Recolecta todos los tags únicos."""
        tags = {node.tag}

        for child in node.children:
            tags.update(self._collect_unique_tags(child))

        return sorted(tags)

    def _summarize_attributes(self, node: XMLNode) -> Dict[str, Any]:
        """Resume la distribución de atributos."""
        all_attributes = {}

        def collect_attrs(current_node: XMLNode):
            for attr_name in current_node.attributes:
                all_attributes[attr_name] = all_attributes.get(attr_name, 0) + 1

            for child in current_node.children:
                collect_attrs(child)

        collect_attrs(node)

        return {
            'total_unique_attributes': len(all_attributes),
            'most_common': dict(sorted(all_attributes.items(),
                                       key=lambda x: x[1],
                                       reverse=True)[:10])
        }

    def _summarize_labels(self, node: XMLNode) -> Dict[str, Any]:
        """Resume la distribución de labels por idioma."""
        language_counts = {}

        def collect_labels(current_node: XMLNode):
            for lang in current_node.labels:
                language_counts[lang] = language_counts.get(lang, 0) + 1

            for child in current_node.children:
                collect_labels(child)

        collect_labels(node)

        return {
            'total_languages': len(language_counts),
            'languages': dict(sorted(language_counts.items()))
        }

    def create_flattened_view(self, document: XMLDocument) -> List[Dict[str, Any]]:
        """
        Crea una vista aplanada del documento para fácil navegación.
        """
        flattened = []

        def flatten_node(current_node: XMLNode, path: str = ""):
            current_path = f"{path}/{current_node.tag}"
            if current_node.technical_id:
                current_path = f"{current_path}[@id='{current_node.technical_id}']"

            flattened.append({
                'path': current_path,
                'node': self._normalize_node(current_node),
                'breadcrumb': self._create_breadcrumb(current_node)
            })

            for child in current_node.children:
                flatten_node(child, current_path)

        flatten_node(document.root)
        return flattened

    def _create_breadcrumb(self, node: XMLNode) -> List[Dict[str, str]]:
        """Crea un breadcrumb desde la raíz hasta el nodo."""
        breadcrumb = []
        current = node

        while current:
            breadcrumb.insert(0, {
                'tag': current.tag,
                'technical_id': current.technical_id,
                'sibling_order': current.sibling_order
            })
            current = current.parent

        return breadcrumb