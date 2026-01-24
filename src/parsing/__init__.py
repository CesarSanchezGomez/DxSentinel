"""
Módulo de parseo XML multi-instancia para SAP SuccessFactors.
Parseo agnóstico que se adapta a cualquier configuración válida del Succession Data Model.
"""

from typing import Any, Dict
from .xml_loader import XMLLoader
from .xml_parser import XMLParser,parse_multiple_xml_files
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
    # Clases principales
    'XMLLoader',
    'XMLParser',
    'XMLNormalizer',
    'XMLNode',
    'XMLDocument',
    'NodeType',

    # Excepciones
    'XMLParsingError',
    'XMLValidationError',
    'XMLStructureError',
    'XMLMetadataError',
    'UnsupportedXMLFeatureError',
    'ConfigurationAgnosticError',

    # Funciones de conveniencia
    'parse_successfactors_xml'
]


def parse_successfactors_xml(file_path: str, source_name: str = None) -> Dict[str, Any]:
    """
    Función de conveniencia para parsear XML de SuccessFactors.
    
    Args:
        file_path: Ruta al archivo XML
        source_name: Identificador de la instancia
        
    Returns:
        Dict normalizado con toda la metadata
    """
    # Cargar XML
    loader = XMLLoader()
    xml_root = loader.load_from_file(file_path, source_name)

    # Parsear estructura
    parser = XMLParser()
    document = parser.parse_document(xml_root, source_name)

    # Normalizar
    normalizer = XMLNormalizer()
    normalized = normalizer.normalize_document(document)

    return normalized
# En __init__.py del módulo parsing
def parse_successfactors_with_csf(main_xml_path: str, csf_xml_path: str = None) -> Dict[str, Any]:
    """
    Parsea el XML principal y opcionalmente un CSF, fusionándolos.
    
    Args:
        main_xml_path: Ruta al XML principal (SDM)
        csf_xml_path: Ruta al XML CSF (Country Specific Features)
        
    Returns:
        Dict normalizado con toda la metadata fusionada
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