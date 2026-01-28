from typing import Dict, List, Optional, Any, Tuple
import xml.etree.ElementTree as ET
import re

from .xml_elements import XMLNode, XMLDocument, NodeType
from .xml_normalizer import XMLNormalizer
from .xml_loader import XMLLoader


class XMLParser:
    """
    Parser agnóstico que se adapta a la estructura del XML.
    """

    LABEL_PATTERNS = {
        'label': re.compile(r'.*[Ll]abel.*'),
        'description': re.compile(r'.*[Dd]esc.*'),
        'name': re.compile(r'.*[Nn]ame.*'),
        'title': re.compile(r'.*[Tt]itle.*')
    }

    LANGUAGE_PATTERN = re.compile(r'^[a-z]{2}(-[A-Za-z]{2,})?$')
    HRIS_ELEMENT_PATTERN = re.compile(r'.*hris.*element.*', re.IGNORECASE)

    ELEMENT_FIELD_MAPPING = {
        'personalInfo': 'start-date',
        'PaymentInfo': 'effectiveStartDate',
        'employmentInfo': 'start-date',
        'globalInfo': 'start-date',
        'homeAddress': 'start-date',
        'jobInfo' : 'start-date',
        'personRelationshipInfo' : 'start-date',
        'compInfo' : 'start-date',
        'payComponentRecurring' : 'start-date'
    
    }
    
    # NUEVA: Constante para elementos a duplicar
    ELEMENT_DUPLICATION_MAPPING = {
        'workPermitInfo': ['RFC', 'CURP'],  # Lista de sufijos limpios
        'homeAddress': ['home', 'fiscal']   # Lista de sufijos limpios
    }

    def __init__(self, element_duplication_mapping: dict = None):
        self._current_depth = 0
        self._node_count = 0
        self._elements_to_process = []  # Para seguimiento post-parsing
        
        # Permitir configuración personalizada de duplicación
        if element_duplication_mapping is not None:
            self.ELEMENT_DUPLICATION_MAPPING = element_duplication_mapping

    def parse_document(self,
                    root: ET.Element,
                    source_name: Optional[str] = None) -> XMLDocument:
        """
        Parsea un documento XML completo con duplicación de elementos.
        """
        self._current_depth = 0
        self._node_count = 0
        self._elements_to_process = []

        namespaces = self._extract_all_namespaces(root)
        version, encoding = self._extract_xml_declaration_metadata(root)

        root_node = self._parse_element(
            element=root,
            parent=None,
            sibling_order=0,
            depth=0,
            namespaces=namespaces
        )

        # DEBUG: Mostrar conteo de elementos a duplicar
        print(f"DEBUG: Found {len(self._elements_to_process)} elements to duplicate")
        
        # POST-PROCESAMIENTO: Duplicar elementos después del parsing completo
        self._process_element_duplications()
        document = XMLDocument(
            root=root_node,
            source_name=source_name,
            namespaces=namespaces,
            version=version,
            encoding=encoding
        )

        return document

    def _parse_element(self,
                       element: ET.Element,
                       parent: Optional[XMLNode],
                       sibling_order: int,
                       depth: int,
                       namespaces: Dict[str, str]) -> XMLNode:
        """
        Parsea recursivamente un elemento y registra elementos para duplicación.
        """
        self._node_count += 1

        tag = self._extract_tag_name(element)
        attributes = self._extract_attributes(element)
        labels = self._extract_labels(element, attributes, namespaces)
        namespace = self._extract_namespace(element, namespaces)

        node = XMLNode(
            tag=tag,
            technical_id=None,
            attributes=attributes,
            labels=labels,
            children=[],
            parent=parent,
            depth=depth,
            sibling_order=sibling_order,
            namespace=namespace,
            text_content=self._extract_text_content(element),
            node_type=NodeType.UNKNOWN
        )

        # Verificar si este elemento necesita duplicación
        should_duplicate, suffixes = self._should_duplicate_element(node)
        if should_duplicate:
            # Registrar para procesamiento posterior
            self._elements_to_process.append({
                'node': node,
                'parent': parent,
                'suffixes': suffixes,
                'sibling_order': sibling_order
            })

        # Procesar inyección de campos de fecha (existente)
        should_inject, field_id = self._should_inject_start_date_field(node)

        if should_inject:
            date_field = self._create_date_field_node(field_id)
            date_field.parent = node
            date_field.depth = depth + 1
            date_field.sibling_order = 0
            node.children.append(date_field)

        # Procesar hijos no-label
        child_index = 0
        for i, child_elem in enumerate(element):
            child_tag = self._extract_tag_name(child_elem)
            if not self._is_label_element(child_tag, child_elem):
                child_node = self._parse_element(
                    element=child_elem,
                    parent=node,
                    sibling_order=child_index,
                    depth=depth + 1,
                    namespaces=namespaces
                )
                node.children.append(child_node)
                child_index += 1

        return node

    def _process_element_duplications(self):
        """
        Procesa la duplicación de todos los elementos registrados.
        Elimina el original y crea elementos duplicados como si siempre hubieran existido.
        """
        for item in self._elements_to_process:
            node = item['node']
            parent = item['parent']
            suffixes = item['suffixes']
            original_sibling_order = item['sibling_order']

            if not parent or not suffixes:
                continue

            # Obtener el ID base original
            base_id = self._get_base_id(node)
            
            # DEBUG
            print(f"DEBUG: Processing duplication for {base_id} with suffixes: {suffixes}")
            
            # Crear elementos duplicados para CADA sufijo
            all_nodes = []
            current_sibling_order = original_sibling_order
            
            for suffix in suffixes:
                # Para el primer sufijo, podríamos renombrar el original
                # Para consistencia, mejor crear todos nuevos
                duplicated = self._duplicate_element_with_suffix(
                    node, 
                    suffix,
                    parent
                )
                
                # Actualizar posición
                duplicated.sibling_order = current_sibling_order
                duplicated.depth = node.depth
                current_sibling_order += 1
                
                all_nodes.append(duplicated)
                
                # DEBUG
                new_id = duplicated.technical_id or duplicated.attributes.get('id', '')
                print(f"DEBUG: Created duplicate with ID: {new_id}")

            # IMPORTANTE: NO agregar el nodo original a la lista
            # Solo mantener los duplicados como si fueran los únicos que existieron
            
            # Reemplazar el original por los duplicados
            self._replace_node_in_parent(parent, node, all_nodes)
            
            # DEBUG: Verificar reemplazo
            print(f"DEBUG: Replaced original {base_id} with {len(all_nodes)} duplicates")

    def _rename_element_with_suffix(self, 
                                node: XMLNode, 
                                suffix: str, 
                                suffix_key: str):
        """
        Renombra un elemento existente con un sufijo específico.
        """
        # Actualizar ID técnico del nodo
        original_id = node.technical_id or node.attributes.get('id', '')
        if original_id:
            new_id = f"{original_id}_{suffix}"
            node.technical_id = new_id
            if 'id' in node.attributes:
                node.attributes['id'] = new_id
        
        # Agregar metadata de renombrado
        node.attributes['data-renamed-from'] = original_id
        node.attributes['data-suffix-type'] = suffix_key
        node.attributes['data-suffix-value'] = suffix
        
        # Actualizar labels si existen
        for lang, label in node.labels.items():
            if label:  # Solo actualizar si hay label
                node.labels[lang] = f"{label} ({suffix_key.upper()}: {suffix})"
        
        # Actualizar todos los IDs dentro del árbol
        self._update_ids_in_cloned_tree(node, suffix)

    def _replace_node_in_parent(self, 
                               parent: XMLNode, 
                               original: XMLNode, 
                               replacements: List[XMLNode]):
        """
        Reemplaza un nodo por una lista de nodos en el padre.
        """
        if not parent:
            return

        new_children = []
        replaced = False
        
        for child in parent.children:
            if child == original:
                # Reemplazar el original por todos los nodos
                new_children.extend(replacements)
                replaced = True
            else:
                new_children.append(child)
        
        # Si no se encontró (caso extremo), agregar al final
        if not replaced:
            new_children.extend(replacements)
        
        parent.children = new_children
        
        # Re-indexar sibling orders
        for i, child in enumerate(parent.children):
            child.sibling_order = i

    def _should_duplicate_element(self, node: XMLNode) -> tuple[bool, list]:
        """
        Determina si un elemento debe ser duplicado y devuelve los sufijos.
        """
        # Buscar por ID técnico
        element_id = node.technical_id or node.attributes.get('id', '')
        
        if element_id and element_id in self.ELEMENT_DUPLICATION_MAPPING:
            suffixes = self.ELEMENT_DUPLICATION_MAPPING[element_id]
            return True, suffixes
        
        return False, []

    def _deep_clone_node(self, node: XMLNode, parent: Optional[XMLNode] = None) -> XMLNode:
        """
        Crea una copia profunda completa de un nodo, incluyendo todos sus hijos.
        """
        cloned = XMLNode(
            tag=node.tag,
            technical_id=node.technical_id,
            attributes=node.attributes.copy(),
            labels=node.labels.copy(),
            children=[],
            parent=parent,
            depth=node.depth,
            sibling_order=node.sibling_order,
            namespace=node.namespace,
            text_content=node.text_content,
            node_type=node.node_type
        )
        
        # Clonar recursivamente todos los hijos
        for i, child in enumerate(node.children):
            cloned_child = self._deep_clone_node(child, cloned)
            cloned_child.sibling_order = i
            cloned.children.append(cloned_child)
        
        return cloned

    def _duplicate_element_with_suffix(self, 
                                    original_node: XMLNode, 
                                    suffix: str, 
                                    parent: Optional[XMLNode] = None) -> XMLNode:
        """
        Crea una copia completa de un elemento con un sufijo específico.
        PRESERVA EL ORIGEN (csf/sdm) del elemento original.
        """
        # Crear copia profunda
        duplicated = self._deep_clone_node(original_node, parent)
        
        # Obtener ID base
        base_id = self._get_base_id(original_node)
        
        # Crear nuevo ID limpio
        new_id = f"{base_id}_{suffix}"
        
        # Actualizar IDs
        duplicated.technical_id = new_id
        if 'id' in duplicated.attributes:
            duplicated.attributes['id'] = new_id
        
        # **CRÍTICO: Preservar el origen del elemento**
        # Copiar todos los atributos de origen del original
        origin_attributes = ['data-origin', 'origin', 'source', 'file_type']
        for attr in origin_attributes:
            if attr in original_node.attributes and attr not in duplicated.attributes:
                duplicated.attributes[attr] = original_node.attributes[attr]
        
        # Para elementos CSF, también preservar atributos específicos
        if 'data-origin' in original_node.attributes and original_node.attributes['data-origin'] == 'csf':
            # Preservar todos los atributos CSF
            csf_attrs = ['data-country', 'data-original-id', 'data-full-id']
            for attr in csf_attrs:
                if attr in original_node.attributes:
                    duplicated.attributes[attr] = original_node.attributes[attr]
        
        # NO agregar metadata de duplicación para que parezca original
        # El elemento duplicado debe ser indistinguible del original
        
        # Actualizar labels si existen (solo añadir sufijo al texto)
        if duplicated.labels:
            for lang in duplicated.labels:
                if duplicated.labels[lang]:
                    # Añadir sufijo al final del label
                    duplicated.labels[lang] = f"{duplicated.labels[lang]} ({suffix})"
        
        # Actualizar todos los IDs dentro del árbol clonado
        self._update_ids_in_cloned_tree(duplicated, suffix, base_id)
        
        return duplicated


    def _get_base_id(self, node: XMLNode) -> str:
        """
        Obtiene el ID base sin sufijos duplicados.
        """
        original_id = node.technical_id or node.attributes.get('id', '')
        
        # Si es un ID duplicado anteriormente, extraer el base
        for element_id, suffixes in self.ELEMENT_DUPLICATION_MAPPING.items():
            if original_id == element_id:
                return element_id
            
            for suffix in suffixes:
                if original_id.endswith(f"_{suffix}"):
                    # Es un ID con sufijo, verificar si ya tiene múltiples sufijos
                    parts = original_id.split('_')
                    if len(parts) > 2:
                        # Tiene múltiples sufijos, devolver solo base + último sufijo
                        return f"{parts[0]}_{parts[-1]}"
        
        return original_id

    def _update_ids_in_cloned_tree(self, node: XMLNode, suffix: str, base_id: str):
        """
        Actualiza recursivamente todos los IDs dentro de un árbol clonado.
        PRESERVA los atributos de origen durante la actualización.
        """
        current_id = node.technical_id or node.attributes.get('id', '')
        
        if current_id and base_id in current_id:
            # Crear nuevo ID
            if current_id == base_id:
                new_id = f"{base_id}_{suffix}"
            else:
                # Ya tiene algún sufijo, reemplazar
                parts = current_id.split('_')
                if len(parts) >= 2:
                    # Mantener base + nuevo sufijo
                    new_id = f"{parts[0]}_{suffix}"
                else:
                    new_id = f"{current_id}_{suffix}"
            
            # Actualizar IDs
            node.technical_id = new_id
            if 'id' in node.attributes:
                node.attributes['id'] = new_id
            
            # **CRÍTICO: También actualizar data-original-id si existe**
            if 'data-original-id' in node.attributes:
                # data-original-id debe apuntar al ID original SIN sufijo
                orig_original_id = node.attributes['data-original-id']
                if base_id in orig_original_id:
                    # Extraer el ID base del data-original-id
                    orig_parts = orig_original_id.split('_')
                    if len(orig_parts) > 1 and any(s in orig_parts[-1] for s in ['csf', 'sdm']):
                        # Tiene sufijo de origen, mantenerlo
                        node.attributes['data-original-id'] = f"{orig_parts[0]}_{suffix}_{orig_parts[-1]}"
                    else:
                        node.attributes['data-original-id'] = f"{orig_parts[0]}_{suffix}"
            
            # **CRÍTICO: Actualizar data-full-id si existe (para elementos CSF)**
            if 'data-full-id' in node.attributes:
                full_id = node.attributes['data-full-id']
                if base_id in full_id:
                    # Reemplazar la parte del ID base en el data-full-id
                    node.attributes['data-full-id'] = full_id.replace(base_id, f"{base_id}_{suffix}")
        
        # Actualizar IDs de los hijos recursivamente
        for child in node.children:
            self._update_ids_in_cloned_tree(child, suffix, base_id)

    def _extract_tag_name(self, element: ET.Element) -> str:
        """Extrae el nombre del tag sin namespace."""
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}', 1)[1]
        return tag

    def _extract_attributes(self, element: ET.Element) -> Dict[str, str]:
        """Extrae TODOS los atributos sin filtrar."""
        attributes = {}

        for key, value in element.attrib.items():
            if '}' in key:
                ns_part, attr_name = key.split('}', 1)
                ns_url = ns_part[1:]
                attributes[key] = value
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
        """
        labels: Dict[str, str] = {}

        for attr_name, attr_value in attributes.items():
            is_label = False
            language = None

            for pattern in self.LABEL_PATTERNS.values():
                if pattern.match(attr_name):
                    is_label = True
                    parts = attr_name.split('_')
                    if len(parts) > 1:
                        possible_lang = parts[-1]
                        if '-' in possible_lang or len(possible_lang) in [2, 5, 8]:
                            language = possible_lang
                    break

            if not is_label:
                import re
                lang_suffix_pattern = re.compile(r'_([a-z]{2}(?:-[A-Za-z]{2,})?)$', re.IGNORECASE)
                match = lang_suffix_pattern.search(attr_name)
                if match:
                    is_label = True
                    language = match.group(1)

            if is_label and attr_value and attr_value.strip():
                if language:
                    labels[language.lower()] = attr_value.strip()
                else:
                    labels[f"label_{attr_name}"] = attr_value.strip()

        for child in element:
            child_tag = self._extract_tag_name(child)

            if child_tag.lower() == 'label':
                label_text = child.text.strip() if child.text and child.text.strip() else None

                if not label_text:
                    continue

                child_attrs = self._extract_attributes(child)
                language = None

                for attr_key, attr_value in child_attrs.items():
                    attr_name_lower = attr_key.lower()
                    if any(lang_word in attr_name_lower for lang_word in ['lang', 'language', 'locale']):
                        if attr_value:
                            language = attr_value.lower()
                        break

                if language:
                    labels[language] = label_text
                else:
                    labels['default'] = label_text

        for attr_name, attr_value in attributes.items():
            if (attr_value and
                    len(attr_value.strip()) > 3 and
                    attr_value.strip() != attr_value.strip().upper() and
                    (' ' in attr_value or attr_value[0].isupper())):

                if 'lang' in attr_name.lower() or 'language' in attr_name.lower():
                    continue

                labels[f"attr_{attr_name}"] = attr_value.strip()

        return labels

    def _is_label_element(self, tag_name: str, element: ET.Element) -> bool:
        """
        Determina si un elemento es un label.
        """
        tag_lower = tag_name.lower()

        if any(pattern.match(tag_lower) for pattern in self.LABEL_PATTERNS.values()):
            return True

        if element.text and element.text.strip():
            text = element.text.strip()
            if 2 <= len(text) <= 100 and not text.startswith('http'):
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

            for prefix, url in namespaces.items():
                if url == ns_url:
                    return prefix

            return ns_url

        return None

    def _extract_all_namespaces(self, root: ET.Element) -> Dict[str, str]:
        """
        Extrae todos los namespaces del documento.
        """
        namespaces = {}
        namespaces['xml'] = 'http://www.w3.org/XML/1998/namespace'

        def extract_from_element(elem: ET.Element):
            if '}' in elem.tag:
                ns_url = elem.tag.split('}', 1)[0][1:]
                if ns_url not in namespaces.values():
                    prefix = f"ns{len(namespaces)}"
                    namespaces[prefix] = ns_url

            for key, value in elem.attrib.items():
                if '}' in key:
                    ns_url = key.split('}', 1)[0][1:]
                    if ns_url not in namespaces.values():
                        prefix = f"ns{len(namespaces)}"
                        namespaces[prefix] = ns_url

                if key.startswith('xmlns:'):
                    prefix = key.split(':', 1)[1]
                    namespaces[prefix] = value
                elif key == 'xmlns':
                    namespaces['default'] = value

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

        for attr_name, attr_value in root.attrib.items():
            attr_lower = attr_name.lower()
            if 'version' in attr_lower:
                version = attr_value
            elif 'encoding' in attr_lower:
                encoding = attr_value

        return version, encoding

    def _should_inject_start_date_field(self, node: XMLNode) -> tuple[bool, str]:
        """
        Determina si debemos inyectar un campo de fecha.
        """
        if not self.HRIS_ELEMENT_PATTERN.match(node.tag):
            return False, ""
        
        element_id = node.technical_id or node.attributes.get('id')
        
        if element_id and element_id in self.ELEMENT_FIELD_MAPPING:
            field_id = self.ELEMENT_FIELD_MAPPING[element_id]
            return True, field_id
        
        return False, ""
    
    def _create_date_field_node(self, field_id: str) -> XMLNode:
        """
        Crea el nodo del campo de fecha con el ID específico.
        """
        attributes = {
            'id': field_id,
            'visibility': 'view',
            'required': 'true'
        }
        
        labels = self._get_field_labels(field_id)
        
        field_node = XMLNode(
            tag='hris-field',
            technical_id=field_id,
            attributes=attributes,
            labels=labels,
            children=[],
            parent=None,
            depth=0,
            sibling_order=0,
            namespace=None,
            text_content=None,
            node_type=NodeType.FIELD
        )
        
        return field_node

    def _get_field_labels(self, field_id: str) -> Dict[str, str]:
        """
        Obtiene los labels para el campo según su ID.
        """
        base_labels = {
            'default': 'Start Date',
            'en-debug': 'Start Date',
            'es-mx': 'Fecha del Evento',
            'en-us': 'Start Date'
        }
        
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
        }
        
        if field_id in label_customizations:
            return label_customizations[field_id]
        
        return base_labels


def parse_multiple_xml_files(files: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Parsea múltiples archivos XML y los fusiona en un solo árbol.
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
            
            xml_root = loader.load_from_file(file_path, source_name)
            document = parser.parse_document(xml_root, source_name)
            document.file_type = file_type
            
            if file_type == 'main':
                _mark_nodes_origin(document.root, 'sdm')
            
            documents.append(document)
            
        except Exception as e:
            raise
    
    if len(documents) > 1:
        fused_document = _fuse_csf_with_main(documents)
    else:
        fused_document = documents[0]
    
    normalized = normalizer.normalize_document(fused_document)
    
    return normalized


def _fuse_csf_with_main(documents: List[XMLDocument]) -> XMLDocument:
    """
    Fusiona documentos CSF (Country Specific) con el documento principal.
    """
    main_doc = None
    csf_docs = []
    
    for doc in documents:
        if getattr(doc, 'file_type', 'main') == 'main':
            main_doc = doc
        else:
            csf_docs.append(doc)
    
    if not main_doc:
        main_doc = documents[0]
    
    if not csf_docs:
        return main_doc
    
    for csf_doc in csf_docs:
        main_doc = _merge_country_nodes(main_doc, csf_doc)
    
    return main_doc


def _merge_country_nodes(main_doc: XMLDocument, csf_doc: XMLDocument) -> XMLDocument:
    """
    Fusiona nodos <country> del CSF con el documento principal.
    """
    csf_countries = _find_country_nodes(csf_doc.root)
    
    if not csf_countries:
        return main_doc
    
    for country_node in csf_countries:
        _insert_country_into_main_with_origin(
            main_doc.root, 
            country_node, 
            csf_doc.source_name,
            'csf'
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
    """
    country_code = country_node.technical_id or country_node.attributes.get('id', 'UNKNOWN')
    existing_country = _find_country_by_code(main_root, country_code)
    
    if existing_country:
        _merge_country_content_by_country(existing_country, country_node, country_code, origin)
    else:
        cloned_country = _clone_node_with_origin(country_node, origin, country_code)
        cloned_country.parent = main_root
        cloned_country.depth = main_root.depth + 1
        cloned_country.sibling_order = len(main_root.children)
        main_root.children.append(cloned_country)


def _find_country_nodes(node: XMLNode) -> List[XMLNode]:
    """
    Encuentra recursivamente todos los nodos <country> en el árbol.
    """
    countries = []
    
    if 'country' in node.tag.lower():
        countries.append(node)
    
    for child in node.children:
        countries.extend(_find_country_nodes(child))
    
    return countries


def _clone_node_with_origin(node: XMLNode, origin: str, country_code: str = None) -> XMLNode:
    """
    Crea una copia profunda de un nodo marcando su origen.
    """
    cloned = XMLNode(
        tag=node.tag,
        technical_id=node.technical_id,
        attributes=node.attributes.copy(),
        labels=node.labels.copy(),
        children=[],
        parent=None,
        depth=node.depth,
        sibling_order=node.sibling_order,
        namespace=node.namespace,
        text_content=node.text_content,
        node_type=node.node_type
    )
    
    if origin:
        cloned.attributes['data-origin'] = origin
    
    if country_code:
        cloned.attributes['data-country'] = country_code
    
    if node.technical_id:
        if origin == 'csf':
            pass
        elif origin == 'sdm':
            pass
    
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


def _clone_node(node: XMLNode) -> XMLNode:
    """
    Crea una copia profunda de un nodo.
    """
    cloned = XMLNode(
        tag=node.tag,
        technical_id=node.technical_id,
        attributes=node.attributes.copy(),
        labels=node.labels.copy(),
        children=[],
        parent=None,
        depth=node.depth,
        sibling_order=node.sibling_order,
        namespace=node.namespace,
        text_content=node.text_content,
        node_type=node.node_type
    )
    
    for child in node.children:
        cloned_child = _clone_node(child)
        cloned_child.parent = cloned
        cloned.children.append(cloned_child)
    
    return cloned


def _mark_nodes_origin(node: XMLNode, origin: str):
    """
    Marca recursivamente todos los nodos con su origen.
    """
    if 'data-origin' not in node.attributes:
        node.attributes['data-origin'] = origin
    
    if 'hris' in node.tag.lower() and node.technical_id and origin != 'sdm':
        node.technical_id = f"{node.technical_id}_{origin}"
    
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
    """
    for new_element in new_country.children:
        if 'hris' in new_element.tag.lower() and 'element' in new_element.tag.lower():
            element_id = new_element.technical_id or new_element.attributes.get('id')
            
            existing_element = None
            for child in existing_country.children:
                if ('hris' in child.tag.lower() and 'element' in child.tag.lower() and
                    (child.technical_id or child.attributes.get('id')) == element_id):
                    existing_element = child
                    break
            
            if existing_element:
                _merge_element_fields_by_country(existing_element, new_element, country_code, origin)
            else:
                cloned_element = _clone_node_with_origin(new_element, origin, country_code)
                cloned_element.parent = existing_country
                cloned_element.depth = existing_country.depth + 1
                cloned_element.sibling_order = len(existing_country.children)
                
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
    for new_field in new_element.children:
        if 'hris' in new_field.tag.lower() and 'field' in new_field.tag.lower():
            field_id = new_field.technical_id or new_field.attributes.get('id')
            
            existing_field_found = False
            for existing_field in existing_element.children:
                if ('hris' in existing_field.tag.lower() and 'field' in existing_field.tag.lower() and
                    (existing_field.technical_id or existing_field.attributes.get('id')) == field_id):
                    
                    if 'data-origin' not in existing_field.attributes:
                        existing_field.attributes['data-origin'] = 'sdm'
                    
                    existing_field_found = True
                    break
            
            if not existing_field_found:
                cloned_field = _clone_node_with_origin(new_field, origin, country_code)
                cloned_field.parent = existing_element
                cloned_field.depth = existing_element.depth + 1
                cloned_field.sibling_order = len(existing_element.children)
                
                if origin == 'csf':
                    _generate_country_based_ids(cloned_field, country_code, origin)
                
                existing_element.children.append(cloned_field)


def _generate_country_based_ids(node: XMLNode, country_code: str, origin: str):
    """
    Genera IDs basados en país para elementos CSF.
    """
    if origin == 'sdm':
        return
    
    current_id = node.technical_id or node.attributes.get('id', '')
    
    if not current_id:
        return
    
    node.attributes['data-original-id'] = current_id
    
    if origin == 'csf':
        full_id = f"{country_code}_{current_id}_{origin}"
    else:
        full_id = f"{country_code}_{current_id}"
    
    node.attributes['data-full-id'] = full_id
    node.technical_id = full_id
    
    if 'hris' in node.tag.lower() and 'element' in node.tag.lower():
        for child in node.children:
            if 'hris' in child.tag.lower() and 'field' in child.tag.lower():
                _generate_country_based_ids(child, country_code, origin)