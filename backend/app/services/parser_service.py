from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import time
import logging

# Importar orquestador CORREGIDO
from ...core.parsing.orchestrator import parse_and_store_xml
from ...core.generators.golden_record import GoldenRecordGenerator
from ...core.generators.golden_record.element_processor import ElementProcessor
from ...core.generators.golden_record.csv_generator import CSVGenerator

logger = logging.getLogger(__name__)


class ParserService:

    @staticmethod
    def process_files(
            main_file_path: str,
            csf_file_path: Optional[str],
            language_code: str,
            country_code: Optional[str],
            output_dir: str,
            # PARÁMETROS para metadata - mantener 'id' como espera orchestrator
            id: str,          # ← ¡CORREGIDO! Usar 'id' no 'process_id'
            cliente: str,
            consultor: str
    ) -> Dict:
        """
        Procesa archivos XML para un solo país o sin CSF.
        
        Args:
            main_file_path: Ruta al archivo principal
            csf_file_path: Ruta al archivo CSF (opcional)
            language_code: Código de idioma
            country_code: Código de país (opcional)
            output_dir: Directorio de salida
            id: ID único para metadata (lo espera orchestrator)
            cliente: Nombre del cliente
            consultor: Nombre del consultor
        """
        start_time = datetime.now()

        # USAR orquestador CON PARÁMETROS CORRECTOS
        if csf_file_path:
            # Parsear con CSF
            result = parse_and_store_xml(
                main_xml_path=main_file_path,
                id=id,  # ← ¡CORREGIDO! Usar 'id' directamente
                csf_xml_path=csf_file_path,
                element_duplication_mapping={
                    'workPermitInfo': ['RFC', 'CURP']
                },
                cliente=cliente,    # Obligatorio
                consultor=consultor # Obligatorio
            )
            parsed_model = result['normalized']
        else:
            # Parsear solo archivo principal
            result = parse_and_store_xml(
                main_xml_path=main_file_path,
                id=id,  # ← ¡CORREGIDO! Usar 'id' directamente
                csf_xml_path=None,
                element_duplication_mapping={
                    'workPermitInfo': ['RFC', 'CURP']
                },
                cliente=cliente,    # Obligatorio
                consultor=consultor # Obligatorio
            )
            parsed_model = result['normalized']

        # Log metadata storage info
        logger.info(f"Metadata stored at: {result.get('storage', {}).get('path', 'N/A')}")

        # El resto se mantiene igual
        generator = GoldenRecordGenerator(
            output_dir=output_dir,
            target_country=country_code
        )

        result_files = generator.generate_template(
            parsed_model=parsed_model,
            language_code=language_code
        )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        template_path = Path(result_files["csv"])
        metadata_path = Path(result_files["metadata"])

        field_count = 0
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                if lines:
                    header_fields = lines[0].strip().split(',')
                    field_count = len(header_fields) if header_fields[0] else 0

        return {
            "output_file": str(template_path),
            "metadata_file": str(metadata_path),
            "field_count": field_count,
            "processing_time": processing_time,
            "metadata_storage": result.get('storage', {})
        }

    @staticmethod
    def process_multiple_countries(
            main_file_path: str,
            csf_file_path: Optional[str],
            language_code: str,
            country_codes: List[str],
            output_dir: str,
            # PARÁMETROS para metadata - mantener 'id' como espera orchestrator
            id: str,          # ← ¡CORREGIDO! Usar 'id' no 'process_id'
            cliente: str,
            consultor: str
    ) -> Dict:
        """
        Procesa archivos XML para múltiples países simultáneamente.
        
        Args:
            main_file_path: Ruta al archivo principal
            csf_file_path: Ruta al archivo CSF (opcional)
            language_code: Código de idioma
            country_codes: Lista de códigos de país
            output_dir: Directorio de salida
            id: ID único para metadata (lo espera orchestrator)
            cliente: Nombre del cliente
            consultor: Nombre del consultor
        """
        start_time = time.time()

        logger.info(f"Processing multiple countries: {country_codes}")
        logger.info(f"ID: {id}, Cliente: {cliente}, Consultor: {consultor}")

        # Validar que se proporcionaron países
        if not country_codes or len(country_codes) == 0:
            raise ValueError("Debe proporcionar al menos un código de país")

        # USAR orquestador CON PARÁMETROS CORRECTOS
        csf_paths = [csf_file_path] if csf_file_path else None
        
        # Usar el id proporcionado (lo espera orchestrator)
        result = parse_and_store_xml(
            main_xml_path=main_file_path,
            id=id,  # ← ¡CORREGIDO! Usar 'id' directamente
            csf_xml_path=csf_paths,
            element_duplication_mapping={
                'workPermitInfo': ['RFC', 'CURP']
            },
            cliente=cliente,    # Obligatorio
            consultor=consultor # Obligatorio
        )
        
        parsed_model = result['normalized']
        
        # Log metadata storage info
        logger.info(f"Metadata stored at: {result.get('storage', {}).get('path', 'N/A')}")

        # Procesar con ElementProcessor para MÚLTIPLES países
        logger.info(f"Processing elements for countries: {country_codes}")

        processor = ElementProcessor(target_countries=country_codes)
        golden_record = processor.process_model(parsed_model)

        # Validar que se procesaron elementos
        if not golden_record.get("elements"):
            raise ValueError("No se encontraron elementos para procesar")

        # Generar CSV
        logger.info("Generating CSV output...")

        csv_generator = CSVGenerator(
            target_countries=country_codes,
            language_code=language_code
        )

        output_file, metadata_file = csv_generator.generate(
            golden_record=golden_record,
            output_dir=output_dir
        )

        processing_time = time.time() - start_time

        # Contar campos
        total_fields = sum(elem.get("field_count", 0) for elem in golden_record.get("elements", []))

        result = {
            "output_file": str(output_file),
            "metadata_file": str(metadata_file),
            "field_count": total_fields,
            "processing_time": processing_time,
            "countries_processed": golden_record.get("processed_countries", country_codes),
            "metadata_storage": result.get('storage', {})
        }

        logger.info(f"Processing completed: {result}")
        return result