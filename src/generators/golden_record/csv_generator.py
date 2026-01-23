from typing import Dict, List
import csv
from .element_processor import ElementProcessor
from .language_resolver import GoldenRecordLanguageResolver
from .exceptions import GoldenRecordError


class CSVGenerator:
    """Generates golden_record_template.csv file."""

    def __init__(self):
        self.processor = ElementProcessor()
        self.language_resolver = GoldenRecordLanguageResolver()

    def generate_template_csv(self, parsed_model: Dict, output_path: str,
                              language_code: str) -> str:
        """
        Generates CSV template with translated labels.

        Args:
            parsed_model: Parsed SDM model
            output_path: Output file path
            language_code: Language code for labels

        Returns:
            Path to generated file
        """
        try:
            processed_data = self.processor.process_model(parsed_model)
            elements = processed_data.get("elements", [])

            columns = []
            for element in elements:
                for field in element["fields"]:
                    columns.append({
                        "full_id": field["full_field_id"],
                        "field_id": field["field_id"],
                        "node": field["node"]
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

                writer.writerow([])

            return output_path

        except Exception as e:
            raise GoldenRecordError(f"Error generating template CSV: {str(e)}") from e

    def _get_translated_labels(self, columns: List[Dict], language_code: str) -> Dict[str, str]:
        """Gets translated labels for all columns."""
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
