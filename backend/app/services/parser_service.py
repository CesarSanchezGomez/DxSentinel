# backend/app/services/parser_service.py
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import time
import logging

from ...core.parsing import parse_successfactors_with_csf, parse_successfactors_xml, parse_multiple_xml_files
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
            output_dir: str
    ) -> Dict:
        """
        Procesa archivos XML para un solo país o sin CSF.
        """
        start_time = datetime.now()

        if csf_file_path:
            parsed_model = parse_successfactors_with_csf(main_file_path, csf_file_path)
        else:
            parsed_model = parse_successfactors_xml(main_file_path, "main")

        generator = GoldenRecordGenerator(
            output_dir=output_dir,
            target_country=country_code
        )

        # CAMBIO: generate_template ahora retorna un dict
        result_files = generator.generate_template(
            parsed_model=parsed_model,
            language_code=language_code
        )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Usar el path del CSV
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
            "processing_time": processing_time
        }

    @staticmethod
    def process_multiple_countries(
            main_file_path: str,
            csf_file_path: Optional[str],
            language_code: str,
            country_codes: List[str],
            output_dir: str
    ) -> Dict:
        """
        Procesa archivos XML para múltiples países simultáneamente.

        Args:
            main_file_path: Ruta al archivo SDM principal
            csf_file_path: Ruta al archivo CSF (opcional)
            language_code: Código de idioma (e.g., "en-US")
            country_codes: Lista de códigos de países (e.g., ["MEX", "USA", "CAN"])
            output_dir: Directorio de salida

        Returns:
            Diccionario con información del procesamiento
        """
        start_time = time.time()

        logger.info(f"Processing multiple countries: {country_codes}")

        # Validar que se proporcionaron países
        if not country_codes or len(country_codes) == 0:
            raise ValueError("Debe proporcionar al menos un código de país")

        # Preparar archivos
        files = [
            {
                'path': main_file_path,
                'type': 'main',
                'source_name': Path(main_file_path).name
            }
        ]

        if csf_file_path:
            files.append({
                'path': csf_file_path,
                'type': 'csf',
                'source_name': Path(csf_file_path).name
            })

        # Parsear archivos
        logger.info("Parsing XML files...")
        parsed_model = parse_multiple_xml_files(files)

        # Procesar con ElementProcessor para MÚLTIPLES países
        logger.info(f"Processing elements for countries: {country_codes}")

        # CLAVE: Pasar lista de países
        processor = ElementProcessor(target_countries=country_codes)
        golden_record = processor.process_model(parsed_model)

        # Validar que se procesaron elementos
        if not golden_record.get("elements"):
            raise ValueError("No se encontraron elementos para procesar")

        # Generar CSV
        logger.info("Generating CSV output...")

        # CORRECCIÓN: Pasar target_countries y language_code al constructor
        csv_generator = CSVGenerator(
            target_countries=country_codes,
            language_code=language_code
        )

        # Llamar al método generate con el golden_record ya procesado
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
            "countries_processed": golden_record.get("processed_countries", country_codes)
        }

        logger.info(f"Processing completed: {result}")
        return result