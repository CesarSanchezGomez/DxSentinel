from typing import List, Dict, Any, Optional
from ..models.xml_elements import XMLNode, XMLDocument


def _fuse_csf_with_main(documents: List[XMLDocument]) -> XMLDocument:
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
    countries = []
    
    if 'country' in node.tag.lower():
        countries.append(node)
    
    for child in node.children:
        countries.extend(_find_country_nodes(child))
    
    return countries


def _clone_node_with_origin(node: XMLNode, origin: str, country_code: str = None) -> XMLNode:
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
    
    for child in node.children:
        cloned_child = _clone_node_with_origin(child, origin, country_code)
        cloned_child.parent = cloned
        cloned.children.append(cloned_child)
    
    return cloned


def _find_country_by_code(node: XMLNode, country_code: str) -> Optional[XMLNode]:
    if 'country' in node.tag.lower():
        current_code = node.technical_id or node.attributes.get('id')
        if current_code == country_code:
            return node
    
    for child in node.children:
        result = _find_country_by_code(child, country_code)
        if result:
            return result
    
    return None


def _mark_nodes_origin(node: XMLNode, origin: str):
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