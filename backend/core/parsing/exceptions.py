from typing import Optional


class XMLParsingError(Exception):
    """Error base para todos los errores de parseo XML."""
    
    def __init__(self, message: str, xml_source: Optional[str] = None):
        self.xml_source = xml_source
        self.instance_context = f" (XML: {xml_source})" if xml_source else ""
        super().__init__(f"{message}{self.instance_context}")


class XMLValidationError(XMLParsingError):
    """Error cuando el XML no cumple con formato básico válido."""
    
    def __init__(self, message: str, xml_source: Optional[str] = None):
        super().__init__(f"XML validation failed: {message}", xml_source)


class XMLStructureError(XMLParsingError):
    """Error cuando la estructura del XML es problemática."""
    
    def __init__(self, 
                 message: str, 
                 node_path: Optional[str] = None,
                 xml_source: Optional[str] = None):
        self.node_path = node_path
        context = f" at path: {node_path}" if node_path else ""
        super().__init__(f"XML structure error: {message}{context}", xml_source)


class XMLMetadataError(XMLParsingError):
    """Error relacionado con metadata inconsistente."""
    
    def __init__(self,
                 message: str,
                 metadata_key: Optional[str] = None,
                 xml_source: Optional[str] = None):
        self.metadata_key = metadata_key
        context = f" for metadata: {metadata_key}" if metadata_key else ""
        super().__init__(f"XML metadata error: {message}{context}", xml_source)


class UnsupportedXMLFeatureError(XMLParsingError):
    """Error cuando se encuentra una característica XML no soportada."""
    
    def __init__(self,
                 feature: str,
                 xml_source: Optional[str] = None):
        super().__init__(f"Unsupported XML feature: {feature}", xml_source)


class ConfigurationAgnosticError(Exception):
    """Error que indica que se intentó hacer una suposición sobre la configuración."""
    
    def __init__(self, assumption: str):
        super().__init__(
            f"Configuration assumption detected: {assumption}. "
            "This violates the multi-instance requirement."
        )