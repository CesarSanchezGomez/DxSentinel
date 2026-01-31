from typing import Any, Dict
from .parsers.xml_parser import parse_multiple_xml_files


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