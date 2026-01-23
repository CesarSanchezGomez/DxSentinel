"""
Carga XML desde filesystem sin conocer estructura.
Falla temprano si XML es inválido.
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Union, Optional, Tuple
import gzip
import logging

from .exceptions import XMLValidationError, XMLParsingError

logger = logging.getLogger(__name__)


class XMLLoader:
    """
    Cargador agnóstico de XML.
    No interpreta nodos, solo carga y valida formato básico.
    """

    @staticmethod
    def load_from_file(file_path: Union[str, Path],
                       xml_source: Optional[str] = None) -> ET.Element:
        """
        Carga XML desde archivo.
        
        Args:
            file_path: Ruta al archivo XML o XML.gz
            xml_source: Identificador de la instancia para mensajes de error
        
        Returns:
            ElementTree root element
            
        Raises:
            XMLValidationError: Si el XML no es válido
            FileNotFoundError: Si el archivo no existe
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"XML file not found: {file_path}")

        try:
            # Soporte para archivos comprimidos
            if file_path.suffix == '.gz':
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    content = f.read()
                root = ET.fromstring(content)
            else:
                tree = ET.parse(file_path)
                root = tree.getroot()

            # Validación básica de estructura
            if root is None:
                raise XMLValidationError("Empty XML document", xml_source)

            logger.info(f"XML loaded successfully from {file_path}")
            return root

        except ET.ParseError as e:
            raise XMLValidationError(
                f"Invalid XML format: {str(e)}",
                xml_source
            )
        except UnicodeDecodeError as e:
            raise XMLValidationError(
                f"Encoding error: {str(e)}",
                xml_source
            )
        except Exception as e:
            raise XMLParsingError(
                f"Unexpected error loading XML: {str(e)}",
                xml_source
            )

    @staticmethod
    def load_from_string(xml_string: str,
                         xml_source: Optional[str] = None) -> ET.Element:
        """
        Carga XML desde string.
        
        Args:
            xml_string: String con contenido XML
            xml_source: Identificador de la instancia
            
        Returns:
            ElementTree root element
        """
        try:
            root = ET.fromstring(xml_string)

            if root is None:
                raise XMLValidationError("Empty XML string", xml_source)

            logger.info("XML loaded successfully from string")
            return root

        except ET.ParseError as e:
            raise XMLValidationError(
                f"Invalid XML string: {str(e)}",
                xml_source
            )
        except Exception as e:
            raise XMLParsingError(
                f"Unexpected error parsing XML string: {str(e)}",
                xml_source
            )

    @staticmethod
    def extract_namespaces(root: ET.Element) -> Dict[str, str]:
        """
        Extrae namespaces del elemento raíz.
        
        Args:
            root: Elemento raíz
            
        Returns:
            Diccionario de prefix -> namespace URI
        """
        namespaces = {}

        # Extraer namespaces de atributos
        for key, value in root.attrib.items():
            if key.startswith('xmlns:'):
                prefix = key.split(':', 1)[1]
                namespaces[prefix] = value
            elif key == 'xmlns':
                namespaces['default'] = value

        return namespaces

    @staticmethod
    def get_xml_metadata(root: ET.Element) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrae metadata básica del XML.
        
        Args:
            root: Elemento raíz
            
        Returns:
            Tupla (version, encoding)
        """
        # Nota: ET no expone fácilmente la declaración XML
        # En una implementación real podríamos usar lxml o parsear manualmente
        version = root.get('version') if 'version' in root.attrib else None

        # Encoding no es fácilmente accesible con ElementTree
        encoding = None

        return version, encoding
