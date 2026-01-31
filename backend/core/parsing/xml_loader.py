import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Union, Optional, Tuple
import gzip

from .exceptions import XMLValidationError, XMLParsingError


class XMLLoader:
    """
    Cargador agnóstico de XML.
    """

    @staticmethod
    def load_from_file(file_path: Union[str, Path],
                       xml_source: Optional[str] = None) -> ET.Element:
        """
        Carga XML desde archivo.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"XML file not found: {file_path}")

        try:
            if file_path.suffix == '.gz':
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    content = f.read()
                root = ET.fromstring(content)
            else:
                tree = ET.parse(file_path)
                root = tree.getroot()

            if root is None:
                raise XMLValidationError("Empty XML document", xml_source)

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
        """
        try:
            root = ET.fromstring(xml_string)

            if root is None:
                raise XMLValidationError("Empty XML string", xml_source)

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
        """
        namespaces = {}

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
        """
        version = root.get('version') if 'version' in root.attrib else None
        encoding = None

        return version, encoding