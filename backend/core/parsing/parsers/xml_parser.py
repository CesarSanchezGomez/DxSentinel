from typing import Dict, List, Optional, Any, Tuple
import xml.etree.ElementTree as ET
import re
from ..filters.xml_filter import create_hris_filter 

from ..models.xml_elements import XMLNode, XMLDocument, NodeType
from ..loaders.xml_loader import XMLLoader
from ..normalizers.xml_normalizer import XMLNormalizer
from ..utils.xml_merger import (
    _fuse_csf_with_main,
    _mark_nodes_origin
)


class XMLParser:
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
        'jobInfo': 'start-date',
        'personRelationshipInfo': 'start-date',
        'compInfo': 'start-date',
        'payComponentRecurring': 'start-date'
    }
    
    ELEMENT_DUPLICATION_MAPPING = {
        'workPermitInfo': ['RFC', 'IMMS'],
        'homeAddress': ['home', 'fiscal']
    }

    def __init__(self, element_duplication_mapping: dict = None):
        self._current_depth = 0
        self._node_count = 0
        self._elements_to_process = []
        
        if element_duplication_mapping is not None:
            self.ELEMENT_DUPLICATION_MAPPING = element_duplication_mapping

    def parse_document(self,
                    root: ET.Element,
                    source_name: Optional[str] = None) -> XMLDocument:
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

        should_duplicate, suffixes = self._should_duplicate_element(node)
        if should_duplicate:
            self._elements_to_process.append({
                'node': node,
                'parent': parent,
                'suffixes': suffixes,
                'sibling_order': sibling_order
            })

        should_inject, field_id = self._should_inject_start_date_field(node)
        if should_inject:
            date_field = self._create_date_field_node(field_id)
            date_field.parent = node
            date_field.depth = depth + 1
            date_field.sibling_order = 0
            node.children.append(date_field)

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
        for item in self._elements_to_process:
            node = item['node']
            parent = item['parent']
            suffixes = item['suffixes']
            original_sibling_order = item['sibling_order']

            if not parent or not suffixes:
                continue

            base_id = self._get_base_id(node)
            all_nodes = []
            current_sibling_order = original_sibling_order
            
            for suffix in suffixes:
                duplicated = self._duplicate_element_with_suffix(
                    node, 
                    suffix,
                    parent
                )
                duplicated.sibling_order = current_sibling_order
                duplicated.depth = node.depth
                current_sibling_order += 1
                all_nodes.append(duplicated)

            self._replace_node_in_parent(parent, node, all_nodes)

    def _should_duplicate_element(self, node: XMLNode) -> tuple[bool, list]:
        element_id = node.technical_id or node.attributes.get('id', '')
        
        if element_id and element_id in self.ELEMENT_DUPLICATION_MAPPING:
            suffixes = self.ELEMENT_DUPLICATION_MAPPING[element_id]
            return True, suffixes
        
        return False, []

    def _deep_clone_node(self, node: XMLNode, parent: Optional[XMLNode] = None) -> XMLNode:
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
        
        for i, child in enumerate(node.children):
            cloned_child = self._deep_clone_node(child, cloned)
            cloned_child.sibling_order = i
            cloned.children.append(cloned_child)
        
        return cloned

    def _duplicate_element_with_suffix(self, 
                                    original_node: XMLNode, 
                                    suffix: str, 
                                    parent: Optional[XMLNode] = None) -> XMLNode:
        duplicated = self._deep_clone_node(original_node, parent)
        base_id = self._get_base_id(original_node)
        new_id = f"{base_id}_{suffix}"
        
        duplicated.technical_id = new_id
        if 'id' in duplicated.attributes:
            duplicated.attributes['id'] = new_id
        
        origin_attributes = ['data-origin', 'origin', 'source', 'file_type']
        for attr in origin_attributes:
            if attr in original_node.attributes and attr not in duplicated.attributes:
                duplicated.attributes[attr] = original_node.attributes[attr]
        
        if 'data-origin' in original_node.attributes and original_node.attributes['data-origin'] == 'csf':
            csf_attrs = ['data-country', 'data-original-id', 'data-full-id']
            for attr in csf_attrs:
                if attr in original_node.attributes:
                    duplicated.attributes[attr] = original_node.attributes[attr]
        
        if duplicated.labels:
            for lang in duplicated.labels:
                if duplicated.labels[lang]:
                    duplicated.labels[lang] = f"{duplicated.labels[lang]} ({suffix})"
        
        self._update_ids_in_cloned_tree(duplicated, suffix, base_id)
        
        return duplicated

    def _get_base_id(self, node: XMLNode) -> str:
        original_id = node.technical_id or node.attributes.get('id', '')
        
        for element_id, suffixes in self.ELEMENT_DUPLICATION_MAPPING.items():
            if original_id == element_id:
                return element_id
            
            for suffix in suffixes:
                if original_id.endswith(f"_{suffix}"):
                    parts = original_id.split('_')
                    if len(parts) > 2:
                        return f"{parts[0]}_{parts[-1]}"
        
        return original_id

    def _update_ids_in_cloned_tree(self, node: XMLNode, suffix: str, base_id: str):
        current_id = node.technical_id or node.attributes.get('id', '')
        
        if current_id and base_id in current_id:
            if current_id == base_id:
                new_id = f"{base_id}_{suffix}"
            else:
                parts = current_id.split('_')
                if len(parts) >= 2:
                    new_id = f"{parts[0]}_{suffix}"
                else:
                    new_id = f"{current_id}_{suffix}"
            
            node.technical_id = new_id
            if 'id' in node.attributes:
                node.attributes['id'] = new_id
            
            if 'data-original-id' in node.attributes:
                orig_original_id = node.attributes['data-original-id']
                if base_id in orig_original_id:
                    orig_parts = orig_original_id.split('_')
                    if len(orig_parts) > 1 and any(s in orig_parts[-1] for s in ['csf', 'sdm']):
                        node.attributes['data-original-id'] = f"{orig_parts[0]}_{suffix}_{orig_parts[-1]}"
                    else:
                        node.attributes['data-original-id'] = f"{orig_parts[0]}_{suffix}"
            
            if 'data-full-id' in node.attributes:
                full_id = node.attributes['data-full-id']
                if base_id in full_id:
                    node.attributes['data-full-id'] = full_id.replace(base_id, f"{base_id}_{suffix}")
        
        for child in node.children:
            self._update_ids_in_cloned_tree(child, suffix, base_id)

    def _replace_node_in_parent(self, 
                               parent: XMLNode, 
                               original: XMLNode, 
                               replacements: List[XMLNode]):
        if not parent:
            return

        new_children = []
        replaced = False
        
        for child in parent.children:
            if child == original:
                new_children.extend(replacements)
                replaced = True
            else:
                new_children.append(child)
        
        if not replaced:
            new_children.extend(replacements)
        
        parent.children = new_children
        
        for i, child in enumerate(parent.children):
            child.sibling_order = i

    def _extract_tag_name(self, element: ET.Element) -> str:
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}', 1)[1]
        return tag

    def _extract_attributes(self, element: ET.Element) -> Dict[str, str]:
        attributes = {}
        for key, value in element.attrib.items():
            if '}' in key:
                attributes[key] = value
                attributes[key.split('}', 1)[1]] = value
            else:
                attributes[key] = value
        return attributes

    def _extract_labels(self,
                        element: ET.Element,
                        attributes: Dict[str, str],
                        namespaces: Dict[str, str]) -> Dict[str, str]:
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
        tag_lower = tag_name.lower()
        if any(pattern.match(tag_lower) for pattern in self.LABEL_PATTERNS.values()):
            return True

        if element.text and element.text.strip():
            text = element.text.strip()
            if 2 <= len(text) <= 100 and not text.startswith('http'):
                attrs = self._extract_attributes(element)
                if any('lang' in key.lower() or 'language' in key.lower() for key in attrs.keys()):
                    return True
        return False

    def _extract_text_content(self, element: ET.Element) -> Optional[str]:
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
        if '}' in element.tag:
            ns_url = element.tag.split('}', 1)[0][1:]
            for prefix, url in namespaces.items():
                if url == ns_url:
                    return prefix
            return ns_url
        return None

    def _extract_all_namespaces(self, root: ET.Element) -> Dict[str, str]:
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
        if not self.HRIS_ELEMENT_PATTERN.match(node.tag):
            return False, ""
        
        element_id = node.technical_id or node.attributes.get('id')
        if element_id and element_id in self.ELEMENT_FIELD_MAPPING:
            field_id = self.ELEMENT_FIELD_MAPPING[element_id]
            return True, field_id
        
        return False, ""
    
    def _create_date_field_node(self, field_id: str) -> XMLNode:
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
    loader = XMLLoader()
    parser = XMLParser()
    normalizer = XMLNormalizer()
    
    documents = []
    
    for file_info in files:
        file_path = file_info['path']
        file_type = file_info.get('type', 'main')
        source_name = file_info.get('source_name', file_path)
        
        xml_root = loader.load_from_file(file_path, source_name)
        document = parser.parse_document(xml_root, source_name)
        document.file_type = file_type
        
        if file_type == 'main':
            _mark_nodes_origin(document.root, 'sdm')
        
        # APLICAR FILTRO HRIS (solo para archivos main)
        if file_type == 'main':
            filter_instance = create_hris_filter(filter_csf=False)
            document = filter_instance.filter_document(document, file_type)
        
        documents.append(document)
    
    if len(documents) > 1:
        fused_document = _fuse_csf_with_main(documents)
    else:
        fused_document = documents[0]
    
    normalized = normalizer.normalize_document(fused_document)
    return normalized