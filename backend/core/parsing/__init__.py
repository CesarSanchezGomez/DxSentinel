# __init__.py actualizado
from typing import Any, Dict
from .main import parse_successfactors_with_csf
from .models.xml_elements import XMLNode, XMLDocument, NodeType
from .exceptions.xml_exceptions import (
    XMLParsingError,
    XMLValidationError,
    XMLStructureError,
    XMLMetadataError,
    UnsupportedXMLFeatureError,
    ConfigurationAgnosticError
)
from .loaders.xml_loader import XMLLoader
from .parsers.xml_parser import XMLParser, parse_multiple_xml_files
from .normalizers.xml_normalizer import XMLNormalizer
from .orchestrator import XMLParsingOrchestrator, create_orchestrator, parse_and_store_xml, load_from_metadata
# Agregar import del filtro
from .filters.xml_filter import XMLFilter, create_hris_filter

__version__ = "1.0.0"
__all__ = [
    'XMLLoader',
    'XMLParser',
    'XMLNormalizer',
    'XMLParsingOrchestrator',
    'create_orchestrator',
    'parse_and_store_xml',
    'load_from_metadata',
    'parse_successfactors_with_csf',
    'parse_multiple_xml_files',
    'XMLNode',
    'XMLDocument',
    'NodeType',
    'XMLParsingError',
    'XMLValidationError',
    'XMLStructureError',
    'XMLMetadataError',
    'UnsupportedXMLFeatureError',
    'ConfigurationAgnosticError',
    # Nuevas exportaciones
    'XMLFilter',
    'create_hris_filter'
]