"""
Parser que recorre el XML tal como existe.
Detecta nodos sin asumir tipos fijos.
CORREGIDO: Manejo robusto de namespaces, labels y extracción de metadata.
"""
from typing import Dict, List, Optional, Any, Tuple
import xml.etree.ElementTree as ET
import logging
import re

from .xml_elements import XMLNode, XMLDocument, NodeType

logger = logging.getLogger(__name__)


class XMLParser:
    """
    Parser agnóstico que se adapta a la estructura del XML.
    No hardcodear expectativas sobre nombres o estructura.
    """

    # Patrones para detectar metadata sin asumir nombres
    LABEL_PATTERNS = {
        'label': re.compile(r'.*[Ll]abel.*'),
        'description': re.compile(r'.*[Dd]esc.*'),
        'name': re.compile(r'.*[Nn]ame.*'),
        'title': re.compile(r'.*[Tt]itle.*')
    }

    # Patrón más flexible para idiomas (soporta en-DEBUG, es-MX, etc.)
    LANGUAGE_PATTERN = re.compile(r'^[a-z]{2}(-[A-Za-z]{2,})?$')

    def __init__(self):
        self._current_depth = 0
        self._node_count = 0

    def parse_document(self,
                       root: ET.Element,
                       source_name: Optional[str] = None) -> XMLDocument:
        """
        Parsea un documento XML completo.
        
        Args:
            root: Elemento raíz de ElementTree
            source_name: Identificador de la fuente
            
        Returns:
            XMLDocument con toda la jerarquía
        """
        self._current_depth = 0
        self._node_count = 0

        # Extraer metadata del documento
        namespaces = self._extract_all_namespaces(root)
        version, encoding = self._extract_xml_declaration_metadata(root)

        # Parsear recursivamente desde la raíz
        root_node = self._parse_element(
            element=root,
            parent=None,
            sibling_order=0,
            depth=0,
            namespaces=namespaces
        )

        document = XMLDocument(
            root=root_node,
            source_name=source_name,
            namespaces=namespaces,
            version=version,
            encoding=encoding
        )

        logger.info(f"Parsed XML document: {self._node_count} nodes processed")
        return document

    def _parse_element(self,
                       element: ET.Element,
                       parent: Optional[XMLNode],
                       sibling_order: int,
                       depth: int,
                       namespaces: Dict[str, str]) -> XMLNode:
        """
        Parsea recursivamente un elemento y todos sus hijos.
        CORREGIDO: Manejo robusto de namespaces y extracción de labels.
        """
        self._node_count += 1

        # Extraer información básica
        tag = self._extract_tag_name(element)
        attributes = self._extract_attributes(element)

        # Extraer labels multilenguaje sin asumir estructura
        labels = self._extract_labels(element, attributes, namespaces)

        # Extraer namespace
        namespace = self._extract_namespace(element, namespaces)

        # Procesar primero los hijos que NO son labels
        children: List[XMLNode] = []
        non_label_children_elements = []

        for i, child_elem in enumerate(element):
            child_tag = self._extract_tag_name(child_elem)

            # Solo procesar ahora los hijos que NO son labels
            # Los labels ya fueron procesados en _extract_labels
            if not self._is_label_element(child_tag, child_elem):
                non_label_children_elements.append((i, child_elem))

        # Crear el nodo primero con los labels ya extraídos
        node = XMLNode(
            tag=tag,
            technical_id=None,  # Se establecerá en __post_init__
            attributes=attributes,
            labels=labels,
            children=[],  # Inicialmente vacío
            parent=parent,
            depth=depth,
            sibling_order=sibling_order,
            namespace=namespace,
            text_content=self._extract_text_content(element),
            node_type=NodeType.UNKNOWN
        )

        # Ahora procesar hijos recursivamente (excluyendo labels ya procesados)
        for i, child_elem in non_label_children_elements:
            child_node = self._parse_element(
                element=child_elem,
                parent=node,
                sibling_order=i,
                depth=depth + 1,
                namespaces=namespaces
            )
            children.append(child_node)

        # Asignar los hijos al nodo
        node.children = children

        return node

    def _extract_tag_name(self, element: ET.Element) -> str:
        """
        Extrae el nombre del tag sin namespace.
        """
        tag = element.tag

        # Manejar namespaces
        if '}' in tag:
            # Formato: {namespace}localname
            tag = tag.split('}', 1)[1]

        return tag

    def _extract_attributes(self, element: ET.Element) -> Dict[str, str]:
        """
        Extrae TODOS los atributos sin filtrar.
        CORREGIDO: Maneja namespaces en atributos como xml:lang
        """
        attributes = {}

        for key, value in element.attrib.items():
            # Conservar el nombre original del atributo
            # (incluyendo namespace si existe)
            if '}' in key:
                # Formato: {namespace}attrName
                # Extraer namespace y nombre
                ns_part, attr_name = key.split('}', 1)
                ns_url = ns_part[1:]  # Quitar el '{'
                attributes[key] = value  # Conservar nombre completo

                # También agregar versión sin namespace para fácil acceso
                attributes[attr_name] = value
            else:
                attributes[key] = value

        return attributes

    def _extract_labels(self,
                        element: ET.Element,
                        attributes: Dict[str, str],
                        namespaces: Dict[str, str]) -> Dict[str, str]:
        """
        Extrae labels de todos los idiomas.
        CORREGIDO: Conserva códigos de idioma completos (es-MX, en-US, en-DEBUG).
        """
        labels: Dict[str, str] = {}

        # 1. Buscar labels en atributos del elemento
        for attr_name, attr_value in attributes.items():
            # Verificar si el atributo parece ser un label
            is_label = False
            language = None

            # Patrón 1: Atributo que contiene "label" o similar
            for pattern in self.LABEL_PATTERNS.values():
                if pattern.match(attr_name):
                    is_label = True
                    # Intentar detectar idioma COMPLETO del nombre del atributo
                    parts = attr_name.split('_')
                    if len(parts) > 1:
                        # Verificar si la última parte es un código de idioma
                        possible_lang = parts[-1]
                        # Aceptar cualquier formato de idioma
                        if '-' in possible_lang or len(possible_lang) in [2, 5, 8]:
                            language = possible_lang
                    break

            # Patrón 2: Atributo con sufijo de idioma común
            if not is_label:
                # Patrón más flexible para detectar sufijos de idioma
                import re
                lang_suffix_pattern = re.compile(r'_([a-z]{2}(?:-[A-Za-z]{2,})?)$', re.IGNORECASE)
                match = lang_suffix_pattern.search(attr_name)
                if match:
                    is_label = True
                    language = match.group(1)  # Conservar el código completo

            if is_label and attr_value and attr_value.strip():
                if language:
                    # Usar el código de idioma completo
                    labels[language.lower()] = attr_value.strip()
                else:
                    # Si no se detecta idioma, usar el nombre del atributo como key
                    labels[f"label_{attr_name}"] = attr_value.strip()

        # 2. Buscar labels en elementos hijos <label>
        for child in element:
            child_tag = self._extract_tag_name(child)

            # Verificar si el hijo es un elemento <label>
            if child_tag.lower() == 'label':
                # Extraer texto del label
                label_text = child.text.strip() if child.text and child.text.strip() else None

                if not label_text:
                    continue

                # Extraer idioma de atributos del hijo - CONSERVAR COMPLETO
                child_attrs = self._extract_attributes(child)
                language = None

                # Buscar atributos de idioma
                for attr_key, attr_value in child_attrs.items():
                    # Verificar si es un atributo de idioma
                    attr_name_lower = attr_key.lower()
                    if any(lang_word in attr_name_lower for lang_word in ['lang', 'language', 'locale']):
                        if attr_value:
                            # CONSERVAR EL VALOR COMPLETO del idioma
                            language = attr_value.lower()
                        break

                if language:
                    # Usar el código de idioma COMPLETO como key
                    labels[language] = label_text
                else:
                    # Label sin idioma específico
                    labels['default'] = label_text

        # 3. Para labels sin idioma específico en atributos xml:lang
        # Buscar atributos xml:lang específicos que podrían contener labels
        for attr_name, attr_value in attributes.items():
            # Si el atributo tiene un valor que parece texto descriptivo
            # y no es un atributo de idioma
            if (attr_value and
                    len(attr_value.strip()) > 3 and
                    attr_value.strip() != attr_value.strip().upper() and
                    (' ' in attr_value or attr_value[0].isupper())):

                # Verificar si es un atributo de idioma
                if 'lang' in attr_name.lower() or 'language' in attr_name.lower():
                    continue

                # Podría ser un label implícito
                labels[f"attr_{attr_name}"] = attr_value.strip()

        return labels

    def _is_label_element(self, tag_name: str, element: ET.Element) -> bool:
        """
        Determina si un elemento es un label.
        """
        tag_lower = tag_name.lower()

        # Verificar por nombre de tag
        if any(pattern.match(tag_lower) for pattern in self.LABEL_PATTERNS.values()):
            return True

        # Verificar por contenido (elemento con texto que parece label)
        if element.text and element.text.strip():
            text = element.text.strip()
            # Heurística: texto no muy largo y parece descriptivo
            if 2 <= len(text) <= 100 and not text.startswith('http'):
                # Verificar atributos comunes de labels
                attrs = self._extract_attributes(element)
                if any('lang' in key.lower() or 'language' in key.lower()
                       for key in attrs.keys()):
                    return True

        return False

    def _extract_text_content(self, element: ET.Element) -> Optional[str]:
        """
        Extrae el contenido de texto del elemento de manera robusta.
        """
        if element.text:
            text = element.text.strip()
            if text:
                return text

        # También considerar tail text si es relevante
        if element.tail:
            tail = element.tail.strip()
            if tail:
                return tail

        return None

    def _extract_namespace(self,
                           element: ET.Element,
                           namespaces: Dict[str, str]) -> Optional[str]:
        """
        Extrae el namespace del elemento.
        """
        if '}' in element.tag:
            ns_url = element.tag.split('}', 1)[0][1:]

            # Encontrar el prefix correspondiente
            for prefix, url in namespaces.items():
                if url == ns_url:
                    return prefix

            return ns_url  # Devolver URL si no se encuentra prefix

        return None

    def _extract_all_namespaces(self, root: ET.Element) -> Dict[str, str]:
        """
        Extrae todos los namespaces del documento.
        """
        namespaces = {}

        # Namespace XML estándar
        namespaces['xml'] = 'http://www.w3.org/XML/1998/namespace'

        # Función recursiva para buscar namespaces
        def extract_from_element(elem: ET.Element):
            if '}' in elem.tag:
                ns_url = elem.tag.split('}', 1)[0][1:]
                # Generar un prefix temporal si no existe
                if ns_url not in namespaces.values():
                    # Intentar extraer prefix del tag
                    if ':' in elem.tag:
                        # Tag tiene prefix explícito
                        pass
                    else:
                        # Crear prefix genérico
                        prefix = f"ns{len(namespaces)}"
                        namespaces[prefix] = ns_url

            # Buscar namespaces en atributos
            for attr_name, attr_value in elem.attrib.items():
                if '}' in attr_name:
                    ns_url = attr_name.split('}', 1)[0][1:]
                    if ns_url not in namespaces.values():
                        prefix = f"ns{len(namespaces)}"
                        namespaces[prefix] = ns_url

                # También verificar si el atributo define un namespace
                if attr_name.startswith('xmlns:'):
                    prefix = attr_name.split(':', 1)[1]
                    namespaces[prefix] = attr_value
                elif attr_name == 'xmlns':
                    namespaces['default'] = attr_value

            for child in elem:
                extract_from_element(child)

        extract_from_element(root)
        return namespaces

    def _extract_xml_declaration_metadata(self, root: ET.Element) -> Tuple[Optional[str], Optional[str]]:
        """
        Intenta extraer metadata de la declaración XML.
        """
        version = None
        encoding = None

        # Verificar si hay atributos que puedan ser metadata
        for attr_name, attr_value in root.attrib.items():
            attr_lower = attr_name.lower()
            if 'version' in attr_lower:
                version = attr_value
            elif 'encoding' in attr_lower:
                encoding = attr_value
            elif 'standalone' in attr_lower:
                # Ignorar standalone por ahora
                pass

        return version, encoding

    # Métodos de análisis y estadísticas (sin cambios)
    def detect_structure_patterns(self, document: XMLDocument) -> Dict[str, Any]:
        """
        Detecta patrones en la estructura sin hacer suposiciones.
        Solo para logging/debugging.
        """
        patterns = {
            'total_nodes': self._node_count,
            'max_depth': self._calculate_max_depth(document.root),
            'node_types_distribution': self._count_node_types(document.root),
            'label_languages': self._extract_label_languages(document.root),
            'common_attributes': self._find_common_attributes(document.root)
        }

        return patterns

    def _calculate_max_depth(self, node: XMLNode) -> int:
        """Calcula la profundidad máxima del árbol."""
        if not node.children:
            return node.depth

        max_child_depth = max(self._calculate_max_depth(child) for child in node.children)
        return max(node.depth, max_child_depth)

    def _count_node_types(self, node: XMLNode) -> Dict[str, int]:
        """Cuenta la distribución de tipos de nodos."""
        counts = {}

        type_name = node.node_type.value
        counts[type_name] = counts.get(type_name, 0) + 1

        for child in node.children:
            child_counts = self._count_node_types(child)
            for type_name, count in child_counts.items():
                counts[type_name] = counts.get(type_name, 0) + count

        return counts

    def _extract_label_languages(self, node: XMLNode) -> List[str]:
        """Extrae todos los idiomas de labels encontrados."""
        languages = set(node.labels.keys())

        for child in node.children:
            child_languages = self._extract_label_languages(child)
            languages.update(child_languages)

        # Filtrar keys que no son códigos de idioma
        language_codes = set()
        for lang in languages:
            if self.LANGUAGE_PATTERN.match(lang.split('_')[0]):  # Extraer base del código
                language_codes.add(lang.split('_')[0])  # Solo la parte del idioma

        return sorted(language_codes)

    def _find_common_attributes(self, node: XMLNode) -> Dict[str, int]:
        """Encuentra atributos comunes en el árbol."""
        attribute_counts = {}

        for attr_name in node.attributes:
            # Normalizar nombre de atributo (sin namespace)
            if '}' in attr_name:
                clean_name = attr_name.split('}', 1)[1]
            else:
                clean_name = attr_name

            attribute_counts[clean_name] = attribute_counts.get(clean_name, 0) + 1

        for child in node.children:
            child_counts = self._find_common_attributes(child)
            for attr_name, count in child_counts.items():
                attribute_counts[attr_name] = attribute_counts.get(attr_name, 0) + count

        # Filtrar atributos que aparecen en múltiples nodos
        common = {k: v for k, v in attribute_counts.items() if v > 1}
        return dict(sorted(common.items(), key=lambda x: x[1], reverse=True))
