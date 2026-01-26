from typing import Any, Dict
from .xml_loader import XMLLoader
from .xml_parser import XMLParser, parse_multiple_xml_files
from .xml_normalizer import XMLNormalizer
from .xml_elements import XMLNode, XMLDocument, NodeType
from .exceptions import (
    XMLParsingError,
    XMLValidationError,
    XMLStructureError,
    XMLMetadataError,
    UnsupportedXMLFeatureError,
    ConfigurationAgnosticError
)

__version__ = "1.0.0"
__all__ = [
    'XMLLoader',
    'XMLParser',
    'XMLNormalizer',
    'XMLNode',
    'XMLDocument',
    'NodeType',
    'XMLParsingError',
    'XMLValidationError',
    'XMLStructureError',
    'XMLMetadataError',
    'UnsupportedXMLFeatureError',
    'ConfigurationAgnosticError',
    'parse_successfactors_xml',
    'parse_successfactors_with_csf'
]


def parse_successfactors_xml(file_path: str, source_name: str = None) -> Dict[str, Any]:
    """
    Función de conveniencia para parsear XML de SuccessFactors.
    """
    loader = XMLLoader()
    xml_root = loader.load_from_file(file_path, source_name)

    parser = XMLParser()
    document = parser.parse_document(xml_root, source_name)

    normalizer = XMLNormalizer()
    normalized = normalizer.normalize_document(document)

    return normalized


def parse_successfactors_with_csf(main_xml_path: str, csf_xml_path: str = None) -> Dict[str, Any]:
    """
    Parsea el XML principal y opcionalmente un CSF, fusionándolos.
    """
    files = [
        {
            'path': main_xml_path,
            'type': 'main',
            'source_name': 'SDM_Principal'
        }
    ]
    
    if csf_xml_path:
        files.append({
            'path': csf_xml_path,
            'type': 'csf',
            'source_name': 'CSF_SDM'
        })
    
    return parse_multiple_xml_files(files)