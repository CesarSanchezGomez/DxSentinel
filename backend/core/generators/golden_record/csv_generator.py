from typing import Dict, List, Optional
import csv
from pathlib import Path


class CSVGenerator:

    def __init__(self, target_country: Optional[str] = None):
        from .element_processor import ElementProcessor
        from .language_resolver import GoldenRecordLanguageResolver
        from backend.core.generators.metadata.metadata_generator import MetadataGenerator

        self.processor = ElementProcessor(target_country=target_country)
        self.language_resolver = GoldenRecordLanguageResolver()
        self.metadata_gen = MetadataGenerator()
        self.target_country = target_country

    def generate_template_csv(
            self,
            parsed_model: Dict,
            output_path: str,
            language_code: str
    ) -> str:

        processed_data = self.processor.process_model(parsed_model)
        elements = processed_data.get("elements", [])

        columns = []
        for element in elements:
            for field in element["fields"]:
                columns.append({
                    "full_id": field["full_field_id"],
                    "field_id": field["field_id"],
                    "node": field["node"],
                    "is_country_specific": field.get("is_country_specific", False),
                    "country_code": field.get("country_code"),
                    "element_id": element["element_id"]
                })

        translated_labels = self._get_translated_labels(columns, language_code)

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            technical_header = [col["full_id"] for col in columns]
            writer.writerow(technical_header)

            descriptive_header = [
                translated_labels.get(col["full_id"], col["field_id"])
                for col in columns
            ]
            writer.writerow(descriptive_header)

        metadata = self.metadata_gen.generate_metadata(processed_data, columns)

        csv_path = Path(output_path)
        metadata_path = csv_path.parent / f"{csv_path.stem}_metadata.json"
        self.metadata_gen.save_metadata(metadata, str(metadata_path))

        return output_path

    def _get_translated_labels(self, columns: List[Dict], language_code: str) -> Dict[str, str]:

        labels_dict = {}

        for column in columns:
            field_node = column["node"]
            full_field_id = column["full_id"]

            field_labels = field_node.get("labels", {})
            label, _ = self.language_resolver.resolve_label(field_labels, language_code)

            if not label:
                label = column["field_id"]

            labels_dict[full_field_id] = label

        return labels_dict