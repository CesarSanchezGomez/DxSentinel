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
from .xml_normalizer import XMLNormalizer
from .xml_loader import XMLLoader
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
    
    HRIS_ELEMENT_PATTERN = re.compile(r'.*hris.*element.*', re.IGNORECASE)

    ELEMENT_FIELD_MAPPING = {
    'personalInfo': 'start-date',
    'PaymentInfo': 'effectiveStartDate',
    'employmentInfo': 'hireDate',
    'globalInfo' : 'start-date',
    'homeAddress' : 'start-date'
    # Agregar más mapeos según sea necesario
    # formato: 'element_id': 'field_id_to_inject'
}
    
    # En xml_parser.py, modificar la función
    def _should_inject_start_date_field(self, node: XMLNode) -> tuple[bool, str]:
        """
        Determina si debemos inyectar un campo de fecha.
        Retorna: (debe_inyectar, field_id_a_inyectar)
        """
        # Verificar si el tag coincide con hris-element
        if not self.HRIS_ELEMENT_PATTERN.match(node.tag):
            return False, ""
        
        # Obtener el ID del elemento
        element_id = node.technical_id or node.attributes.get('id')
        
        # Verificar si el ID está en el mapeo
        if element_id and element_id in self.ELEMENT_FIELD_MAPPING:
            field_id = self.ELEMENT_FIELD_MAPPING[element_id]
            return True, field_id
        
        return False, ""
    
    def _create_date_field_node(self, field_id: str) -> XMLNode:
        """
        Crea el nodo del campo de fecha con el ID específico.
        Mantiene toda la estructura estándar, solo cambia el ID.
        """
        # Atributos del campo - ID dinámico según el mapeo
        attributes = {
            'id': field_id,
            'visibility': 'view',
            'required': 'true'
        }
        
        # Labels multilenguaje (pueden personalizarse por field_id si es necesario)
        labels = self._get_field_labels(field_id)
        
        # Crear el nodo del campo
        field_node = XMLNode(
            tag='hris-field',
            technical_id=field_id,
            attributes=attributes,
            labels=labels,
            children=[],  # Sin hijos adicionales
            parent=None,  # Se establecerá después
            depth=0,      # Se ajustará según el padre
            sibling_order=0,  # Se ajustará
            namespace=None,
            text_content=None,
            node_type=NodeType.FIELD
        )
        
        return field_node
    def _get_field_labels(self, field_id: str) -> Dict[str, str]:
        """
        Obtiene los labels para el campo según su ID.
        Puede personalizarse por tipo de campo.
        """
        # Labels base que se aplican a todos
        base_labels = {
            'default': 'Start Date',
            'en-debug': 'Start Date',
            'es-mx': 'Fecha del Evento',
            'en-us': 'Start Date'
        }
        
        # Personalizar según el ID del campo
        label_customizations = {
            'effectiveStartDate': {
                'default': 'Effective Start Date',
                'en-debug': 'Effective Start Date',
                'es-mx': 'Fecha de Inicio Efectiva',
                'en-us': 'Effective Start Date'
            },
            'hireDate': {
                'default': 'Hire Date',
                'en-debug': 'Hire Date',
                'es-mx': 'Fecha de Contratación',
                'en-us': 'Hire Date'
            }
            # Agregar más personalizaciones según sea necesario
        }
        
        # Usar personalización si existe, si no usar base
        if field_id in label_customizations:
            return label_customizations[field_id]
        
        return base_labels
    
    def _parse_element(self,
                       element: ET.Element,
                       parent: Optional[XMLNode],
                       sibling_order: int,
                       depth: int,
                       namespaces: Dict[str, str]) -> XMLNode:
        """
        Parsea recursivamente un elemento y todos sus hijos.
        MODIFICADO: Inyecta campos de fecha según mapeo en hris-elements específicos.
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
        
        # PUNTO CRÍTICO: Verificar si debemos inyectar un campo de fecha
        should_inject, field_id = self._should_inject_start_date_field(node)
        
        if should_inject:
            # Crear el campo con el ID específico del mapeo
            date_field = self._create_date_field_node(field_id)
            
            # Ajustar propiedades del campo para que sea hijo del nodo actual
            date_field.parent = node
            date_field.depth = depth + 1
            # Agregar como primer hijo (orden 0)
            date_field.sibling_order = 0
            children.append(date_field)
            
            # Ajustar sibling_order de los hijos originales
            for i, child_elem in non_label_children_elements:
                child_node = self._parse_element(
                    element=child_elem,
                    parent=node,
                    sibling_order=i + 1,  # +1 porque el campo inyectado es el 0
                    depth=depth + 1,
                    namespaces=namespaces
                )
                children.append(child_node)
        else:
            # Procesar hijos normalmente (sin campo inyectado)
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
    


def parse_multiple_xml_files(files: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Parsea múltiples archivos XML y los fusiona en un solo árbol.
    MARCA el origen de cada nodo.
    """
    loader = XMLLoader()
    parser = XMLParser()
    normalizer = XMLNormalizer()
    
    documents = []
    
    for file_info in files:
        try:
            file_path = file_info['path']
            file_type = file_info.get('type', 'main')
            source_name = file_info.get('source_name', file_path)
            
            # Cargar XML
            xml_root = loader.load_from_file(file_path, source_name)
            
            # Parsear estructura
            document = parser.parse_document(xml_root, source_name)
            
            # Agregar metadata del tipo de archivo
            document.file_type = file_type
            
            # MARCAR TODOS LOS NODOS DEL SDM PRINCIPAL
            if file_type == 'main':
                _mark_nodes_origin(document.root, 'sdm')
            
            documents.append(document)
            
            print(f"✅ Parseado: {file_path} (tipo: {file_type}, origen: {'sdm' if file_type == 'main' else 'csf'})")
            
        except Exception as e:
            print(f"❌ Error parseando {file_info.get('path')}: {e}")
            raise
    
    # Fusionar documentos si hay más de uno
    if len(documents) > 1:
        fused_document = _fuse_csf_with_main(documents)
    else:
        fused_document = documents[0]
    
    # Normalizar el documento fusionado
    normalized = normalizer.normalize_document(fused_document)
    
    return normalized

def _fuse_csf_with_main(documents: List[XMLDocument]) -> XMLDocument:
    """
    Fusiona documentos CSF (Country Specific) con el documento principal.
    Busca nodos <country> en CSF y los inserta en la estructura principal.
    """
    # Identificar documento principal y CSF
    main_doc = None
    csf_docs = []
    
    for doc in documents:
        if getattr(doc, 'file_type', 'main') == 'main':
            main_doc = doc
        else:
            csf_docs.append(doc)
    
    if not main_doc:
        main_doc = documents[0]  # Fallback al primer documento
    
    # Si no hay CSF, retornar el principal
    if not csf_docs:
        return main_doc
    
    # Fusionar cada documento CSF
    for csf_doc in csf_docs:
        main_doc = _merge_country_nodes(main_doc, csf_doc)
    
    return main_doc

def _merge_country_nodes(main_doc: XMLDocument, csf_doc: XMLDocument) -> XMLDocument:
    """
    Fusiona nodos <country> del CSF con el documento principal.
    MARCA los elementos del CSF para identificar su origen.
    """
    # Buscar nodos <country> en el documento CSF
    csf_countries = _find_country_nodes(csf_doc.root)
    
    if not csf_countries:
        print(f"⚠️  No se encontraron nodos <country> en {csf_doc.source_name}")
        return main_doc
    
    print(f"🔍 Encontrados {len(csf_countries)} nodos <country> en CSF")
    
    # Para cada país del CSF, insertarlo en el documento principal
    for country_node in csf_countries:
        _insert_country_into_main_with_origin(
            main_doc.root, 
            country_node, 
            csf_doc.source_name,
            'csf'  # Marcar origen
        )
    
    return main_doc

def _insert_country_into_main_with_origin(
    main_root: XMLNode, 
    country_node: XMLNode, 
    source_name: str,
    origin: str = 'csf'
):
    """
    Inserta un nodo país del CSF en la estructura principal.
    Marca con origen y país.
    """
    # Obtener el código del país
    country_code = country_node.technical_id or country_node.attributes.get('id', 'UNKNOWN')
    
    # Verificar si ya existe un país con este código en el main
    existing_country = _find_country_by_code(main_root, country_code)
    
    if existing_country:
        print(f"  🔄 País '{country_code}' ya existe, fusionando con origen '{origin}'...")
        _merge_country_content_by_country(existing_country, country_node, country_code, origin)
    else:
        print(f"  ➕ Insertando nuevo país '{country_code}' desde {source_name} (origen: {origin})")
        # Clonar el nodo país con origen y código de país
        cloned_country = _clone_node_with_origin(country_node, origin, country_code)
        
        # Ajustar jerarquía
        cloned_country.parent = main_root
        cloned_country.depth = main_root.depth + 1
        cloned_country.sibling_order = len(main_root.children)
        
        # Agregar como hijo del root
        main_root.children.append(cloned_country)

def _find_country_nodes(node: XMLNode) -> List[XMLNode]:
    """
    Encuentra recursivamente todos los nodos <country> en el árbol.
    """
    countries = []
    
    # Buscar por tag (case insensitive)
    if 'country' in node.tag.lower():
        countries.append(node)
    
    # Buscar recursivamente en hijos
    for child in node.children:
        countries.extend(_find_country_nodes(child))
    
    return countries

def _insert_country_into_main(main_root: XMLNode, country_node: XMLNode, source_name: str):
    """
    Inserta un nodo país del CSF en la estructura principal.
    Estrategia: Agregar como hijo directo del root si no existe.
    """
    # Obtener el código del país
    country_code = country_node.technical_id or country_node.attributes.get('id', 'UNKNOWN')
    
    # Verificar si ya existe un país con este código en el main
    existing_country = _find_country_by_code(main_root, country_code)
    
    if existing_country:
        print(f"  🔄 País '{country_code}' ya existe en main, fusionando contenido...")
        _merge_country_content(existing_country, country_node)
    else:
        print(f"  ➕ Insertando nuevo país '{country_code}' desde {source_name}")
        # Clonar el nodo país (sin referencias al documento original)
        cloned_country = _clone_node(country_node)
        
        # Ajustar jerarquía
        cloned_country.parent = main_root
        cloned_country.depth = main_root.depth + 1
        cloned_country.sibling_order = len(main_root.children)
        
        # Agregar como hijo del root
        main_root.children.append(cloned_country)

def _clone_node_with_origin(node: XMLNode, origin: str, country_code: str = None) -> XMLNode:
    """
    Crea una copia profunda de un nodo marcando su origen.
    Mantiene IDs limpios: [country_][elementId]_[origin] solo si es necesario.
    """
    # Crear nuevo nodo con propiedades básicas
    cloned = XMLNode(
        tag=node.tag,
        technical_id=node.technical_id,
        attributes=node.attributes.copy(),
        labels=node.labels.copy(),
        children=[],  # Inicialmente vacío
        parent=None,  # Se establecerá después
        depth=node.depth,
        sibling_order=node.sibling_order,
        namespace=node.namespace,
        text_content=node.text_content,
        node_type=node.node_type
    )
    
    # AGREGAR ATRIBUTO DE ORIGEN y PAÍS
    if origin:
        cloned.attributes['data-origin'] = origin
    
    if country_code:
        cloned.attributes['data-country'] = country_code
    
    # NUEVO: Modificar technical_id SOLO si es necesario
    # Mantener estructura: [country_][elementId]_[origin]
    # Pero solo agregar _origin si no es 'sdm' (SDM se queda limpio)
    if node.technical_id:
        if origin == 'csf':
            # Para CSF, mantener el ID original pero agregar atributos
            # NO modificar technical_id aquí, solo en la fusión
            pass
        elif origin == 'sdm':
            # SDM mantiene ID limpio
            pass
    
    # Clonar hijos recursivamente con el mismo origen y país
    for child in node.children:
        cloned_child = _clone_node_with_origin(child, origin, country_code)
        cloned_child.parent = cloned
        cloned.children.append(cloned_child)
    
    return cloned

def _find_country_by_code(node: XMLNode, country_code: str) -> Optional[XMLNode]:
    """
    Busca un nodo país por su código.
    """
    if 'country' in node.tag.lower():
        current_code = node.technical_id or node.attributes.get('id')
        if current_code == country_code:
            return node
    
    for child in node.children:
        result = _find_country_by_code(child, country_code)
        if result:
            return result
    
    return None

def _merge_country_content_with_origin(
    existing_country: XMLNode, 
    new_country: XMLNode, 
    origin: str
):
    """
    Fusiona el contenido de un país del CSF con uno existente.
    MARCA los elementos del CSF con su origen.
    """
    # Para cada hris-element del nuevo país
    for new_element in new_country.children:
        if 'hris' in new_element.tag.lower() and 'element' in new_element.tag.lower():
            element_id = new_element.technical_id or new_element.attributes.get('id')
            
            # Buscar si ya existe este elemento en el país existente
            existing_element = None
            for child in existing_country.children:
                if ('hris' in child.tag.lower() and 'element' in child.tag.lower() and
                    (child.technical_id or child.attributes.get('id')) == element_id):
                    existing_element = child
                    break
            
            if existing_element:
                # Fusionar campos del elemento marcando origen CSF
                _merge_element_fields_with_origin(existing_element, new_element, origin)
            else:
                # Agregar el nuevo elemento al país existente CON ORIGEN
                cloned_element = _clone_node_with_origin(new_element, origin)
                cloned_element.parent = existing_country
                cloned_element.depth = existing_country.depth + 1
                cloned_element.sibling_order = len(existing_country.children)
                existing_country.children.append(cloned_element)

def _merge_country_content(existing_country: XMLNode, new_country: XMLNode):
    """
    Fusiona el contenido de un país del CSF con uno existente.
    """
    # Para cada hris-element del nuevo país
    for new_element in new_country.children:
        if 'hris' in new_element.tag.lower() and 'element' in new_element.tag.lower():
            element_id = new_element.technical_id or new_element.attributes.get('id')
            
            # Buscar si ya existe este elemento en el país existente
            existing_element = None
            for child in existing_country.children:
                if ('hris' in child.tag.lower() and 'element' in child.tag.lower() and
                    (child.technical_id or child.attributes.get('id')) == element_id):
                    existing_element = child
                    break
            
            if existing_element:
                # Fusionar campos del elemento
                _merge_element_fields(existing_element, new_element)
            else:
                # Agregar el nuevo elemento al país existente
                cloned_element = _clone_node(new_element)
                cloned_element.parent = existing_country
                cloned_element.depth = existing_country.depth + 1
                cloned_element.sibling_order = len(existing_country.children)
                existing_country.children.append(cloned_element)

def _merge_element_fields(existing_element: XMLNode, new_element: XMLNode):
    """
    Fusiona los campos (hris-field) de un elemento.
    """
    # Para cada campo del nuevo elemento
    for new_field in new_element.children:
        if 'hris' in new_field.tag.lower() and 'field' in new_field.tag.lower():
            field_id = new_field.technical_id or new_field.attributes.get('id')
            
            # Verificar si ya existe este campo
            field_exists = False
            for existing_field in existing_element.children:
                if ('hris' in existing_field.tag.lower() and 'field' in existing_field.tag.lower() and
                    (existing_field.technical_id or existing_field.attributes.get('id')) == field_id):
                    field_exists = True
                    break
            
            if not field_exists:
                # Agregar el nuevo campo
                cloned_field = _clone_node(new_field)
                cloned_field.parent = existing_element
                cloned_field.depth = existing_element.depth + 1
                cloned_field.sibling_order = len(existing_element.children)
                existing_element.children.append(cloned_field)

def _clone_node(node: XMLNode) -> XMLNode:
    """
    Crea una copia profunda de un nodo (sin referencias a hijos originales).
    """
    # Crear nuevo nodo con propiedades básicas
    cloned = XMLNode(
        tag=node.tag,
        technical_id=node.technical_id,
        attributes=node.attributes.copy(),
        labels=node.labels.copy(),
        children=[],  # Inicialmente vacío
        parent=None,  # Se establecerá después
        depth=node.depth,
        sibling_order=node.sibling_order,
        namespace=node.namespace,
        text_content=node.text_content,
        node_type=node.node_type
    )
    
    # Clonar hijos recursivamente
    for child in node.children:
        cloned_child = _clone_node(child)
        cloned_child.parent = cloned
        cloned.children.append(cloned_child)
    
    return cloned
def _merge_country_content_with_origin(
    existing_country: XMLNode, 
    new_country: XMLNode, 
    origin: str
):
    """
    Fusiona el contenido de un país del CSF con uno existente.
    MARCA los elementos del CSF con su origen.
    """
    # Para cada hris-element del nuevo país
    for new_element in new_country.children:
        if 'hris' in new_element.tag.lower() and 'element' in new_element.tag.lower():
            element_id = new_element.technical_id or new_element.attributes.get('id')
            
            # Buscar si ya existe este elemento en el país existente
            existing_element = None
            for child in existing_country.children:
                if ('hris' in child.tag.lower() and 'element' in child.tag.lower() and
                    (child.technical_id or child.attributes.get('id')) == element_id):
                    existing_element = child
                    break
            
            if existing_element:
                # Fusionar campos del elemento marcando origen CSF
                _merge_element_fields_with_origin(existing_element, new_element, origin)
            else:
                # Agregar el nuevo elemento al país existente CON ORIGEN
                cloned_element = _clone_node_with_origin(new_element, origin)
                cloned_element.parent = existing_country
                cloned_element.depth = existing_country.depth + 1
                cloned_element.sibling_order = len(existing_country.children)
                existing_country.children.append(cloned_element)

def _merge_element_fields_with_origin(
    existing_element: XMLNode, 
    new_element: XMLNode, 
    origin: str
):
    """
    Fusiona los campos (hris-field) de un elemento.
    MARCA los campos del CSF para identificar su origen.
    """
    # Para cada campo del nuevo elemento
    for new_field in new_element.children:
        if 'hris' in new_field.tag.lower() and 'field' in new_field.tag.lower():
            field_id = new_field.technical_id or new_field.attributes.get('id')
            
            # Verificar si ya existe este campo
            field_exists = False
            for existing_field in existing_element.children:
                if ('hris' in existing_field.tag.lower() and 'field' in existing_field.tag.lower() and
                    (existing_field.technical_id or existing_field.attributes.get('id')) == field_id):
                    # Campo ya existe, marcar con origen si no está marcado
                    if 'data-origin' not in existing_field.attributes:
                        existing_field.attributes['data-origin'] = 'sdm'  # Asumir que el existente es SDM
                    
                    # Agregar también el campo CSF como duplicado pero marcado
                    cloned_field = _clone_node_with_origin(new_field, origin)
                    cloned_field.parent = existing_element
                    cloned_field.depth = existing_element.depth + 1
                    cloned_field.sibling_order = len(existing_element.children)
                    
                    # Modificar el ID para evitar colisión
                    cloned_field.technical_id = f"{field_id}_{origin}"
                    if 'id' in cloned_field.attributes:
                        cloned_field.attributes['id'] = f"{field_id}_{origin}"
                    
                    existing_element.children.append(cloned_field)
                    field_exists = True
                    break
            
            if not field_exists:
                # Agregar el nuevo campo CON ORIGEN
                cloned_field = _clone_node_with_origin(new_field, origin)
                cloned_field.parent = existing_element
                cloned_field.depth = existing_element.depth + 1
                cloned_field.sibling_order = len(existing_element.children)
                existing_element.children.append(cloned_field)

def _mark_nodes_origin(node: XMLNode, origin: str):
    """
    Marca recursivamente todos los nodos con su origen.
    """
    # Agregar atributo de origen
    if 'data-origin' not in node.attributes:
        node.attributes['data-origin'] = origin
    
    # Modificar technical_id para incluir origen si es un hris-element o field
    if 'hris' in node.tag.lower() and node.technical_id and origin != 'sdm':
        # Solo modificar si no es SDM (SDM se queda como está)
        node.technical_id = f"{node.technical_id}_{origin}"
    
    # Marcar hijos recursivamente
    for child in node.children:
        _mark_nodes_origin(child, origin)

def _merge_country_content_by_country(
    existing_country: XMLNode, 
    new_country: XMLNode, 
    country_code: str,
    origin: str
):
    """
    Fusiona el contenido de un país del CSF con uno existente.
    Genera IDs con estructura: [country_][fieldId]_[origin]
    """
    # Para cada hris-element del nuevo país
    for new_element in new_country.children:
        if 'hris' in new_element.tag.lower() and 'element' in new_element.tag.lower():
            element_id = new_element.technical_id or new_element.attributes.get('id')
            
            # Buscar si ya existe este elemento en el país existente
            existing_element = None
            for child in existing_country.children:
                if ('hris' in child.tag.lower() and 'element' in child.tag.lower() and
                    (child.technical_id or child.attributes.get('id')) == element_id):
                    existing_element = child
                    break
            
            if existing_element:
                # Fusionar campos del elemento
                _merge_element_fields_by_country(existing_element, new_element, country_code, origin)
            else:
                # Agregar el nuevo elemento al país existente
                cloned_element = _clone_node_with_origin(new_element, origin, country_code)
                cloned_element.parent = existing_country
                cloned_element.depth = existing_country.depth + 1
                cloned_element.sibling_order = len(existing_country.children)
                
                # NUEVO: Generar ID con país para elementos CSF
                if origin == 'csf':
                    _generate_country_based_ids(cloned_element, country_code, origin)
                
                existing_country.children.append(cloned_element)

def _merge_element_fields_by_country(
    existing_element: XMLNode, 
    new_element: XMLNode, 
    country_code: str,
    origin: str
):
    """
    Fusiona los campos (hris-field) de un elemento por país.
    """
    # Para cada campo del nuevo elemento
    for new_field in new_element.children:
        if 'hris' in new_field.tag.lower() and 'field' in new_field.tag.lower():
            field_id = new_field.technical_id or new_field.attributes.get('id')
            
            # Verificar si ya existe este campo
            existing_field_found = False
            for existing_field in existing_element.children:
                if ('hris' in existing_field.tag.lower() and 'field' in existing_field.tag.lower() and
                    (existing_field.technical_id or existing_field.attributes.get('id')) == field_id):
                    
                    # Marcar campo existente con origen si no tiene
                    if 'data-origin' not in existing_field.attributes:
                        existing_field.attributes['data-origin'] = 'sdm'
                    
                    existing_field_found = True
                    break
            
            if not existing_field_found:
                # Agregar el nuevo campo
                cloned_field = _clone_node_with_origin(new_field, origin, country_code)
                cloned_field.parent = existing_element
                cloned_field.depth = existing_element.depth + 1
                cloned_field.sibling_order = len(existing_element.children)
                
                # NUEVO: Generar ID con país para campos CSF
                if origin == 'csf':
                    _generate_country_based_ids(cloned_field, country_code, origin)
                
                existing_element.children.append(cloned_field)
def _generate_country_based_ids(node: XMLNode, country_code: str, origin: str):
    """
    Genera IDs basados en país para elementos CSF.
    Estructura: [country_][elementId]_[origin] solo si origin != 'sdm'
    """
    if origin == 'sdm':
        return  # SDM mantiene IDs limpios
    
    current_id = node.technical_id or node.attributes.get('id', '')
    
    if not current_id:
        return
    
    # NUEVA ESTRATEGIA: 
    # 1. Elementos CSF mantienen su ID original en technical_id
    # 2. Agregamos un atributo especial con el ID completo
    # 3. El golden generator usará este atributo especial
    
    # Guardar ID original
    node.attributes['data-original-id'] = current_id
    
    # Generar ID completo: country_elementId_origin (sin origin si es sdm)
    if origin == 'csf':
        full_id = f"{country_code}_{current_id}_{origin}"
    else:
        full_id = f"{country_code}_{current_id}"
    
    # Agregar atributo con ID completo
    node.attributes['data-full-id'] = full_id
    
    # También modificar technical_id para consistencia
    node.technical_id = full_id
    
    # Aplicar recursivamente a hijos si es un elemento
    if 'hris' in node.tag.lower() and 'element' in node.tag.lower():
        for child in node.children:
            if 'hris' in child.tag.lower() and 'field' in child.tag.lower():
                _generate_country_based_ids(child, country_code, origin)