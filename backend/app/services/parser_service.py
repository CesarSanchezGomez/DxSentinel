import sys
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from backend.core.parsing.parsing import parse_successfactors_with_csf, parse_successfactors_xml
from backend.core.generators.golden_record import GoldenRecordGenerator


class ParserService:

    @staticmethod
    def process_files(
            main_file_path: str,
            csf_file_path: Optional[str],
            language_code: str,
            country_code: Optional[str],
            output_dir: str
    ) -> Dict:

        start_time = datetime.now()

        if csf_file_path:
            parsed_model = parse_successfactors_with_csf(main_file_path, csf_file_path)
        else:
            parsed_model = parse_successfactors_xml(main_file_path, "main")

        generator = GoldenRecordGenerator(
            output_dir=output_dir,
            target_country=country_code
        )

        template_file = generator.generate_template(
            parsed_model=parsed_model,
            language_code=language_code
        )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        template_path = Path(template_file)
        field_count = 0
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                if lines:
                    header_fields = lines[0].strip().split(',')
                    field_count = len(header_fields) if header_fields[0] else 0

        return {
            "output_file": template_file,
            "field_count": field_count,
            "processing_time": processing_time
        }