from typing import Dict, List, Optional
import csv
from pathlib import Path


class CSVGenerator:
    EXTRA_GOLDEN_ONLY_FIELDS = [
        {
            "full_id": "homeAddress_address-type",
            "field_id": "address-type",
            "node": {
                "labels": {
                    "en-US": "Address Type",
                    "es-MX": "Tipo de dirección"
                }
            },
            "element_id": "homeAddress",
            "is_country_specific": False,
            "country_code": None
        }
    ]

    def __init__(self, target_countries: Optional[List[str]] = None, language_code: Optional[str] = None,
                 target_country: Optional[str] = None):
        from .element_processor import ElementProcessor
        from .language_resolver import GoldenRecordLanguageResolver
        from backend.core.generators.metadata.metadata_generator import MetadataGenerator

        if target_country and not target_countries:
            target_countries = [target_country]
        elif target_countries and isinstance(target_countries, str):
            target_countries = [target_countries]

        self.processor = ElementProcessor(target_countries=target_countries)
        self.language_resolver = GoldenRecordLanguageResolver()
        self.metadata_gen = MetadataGenerator()
        self.target_countries = target_countries
        self.language_code = language_code

    def generate(
            self,
            golden_record: Dict,
            output_dir: str
    ) -> tuple[str, str]:

        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.target_countries and len(self.target_countries) > 1:
            countries_str = "_".join(sorted(self.target_countries))
            filename = f"golden_record_{countries_str}_{timestamp}.csv"
        elif self.target_countries and len(self.target_countries) == 1:
            filename = f"golden_record_{self.target_countries[0]}_{timestamp}.csv"
        else:
            filename = f"golden_record_{timestamp}.csv"

        output_path = Path(output_dir) / filename

        elements = golden_record.get("elements", [])

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

        present_elements = {e["element_id"] for e in elements}

        if "homeAddress" in present_elements:
            for extra in self.EXTRA_GOLDEN_ONLY_FIELDS:
                if not any(col["full_id"] == extra["full_id"] for col in columns):
                    columns.append(extra.copy())

        language_code = self.language_code or "en-US"

        has_multiple_countries = self.target_countries and len(self.target_countries) > 1

        translated_labels = self._get_translated_labels(
            columns,
            language_code,
            has_multiple_countries
        )

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            technical_header = [col["full_id"] for col in columns]
            writer.writerow(technical_header)

            descriptive_header = [
                translated_labels.get(col["full_id"], col["field_id"])
                for col in columns
            ]
            writer.writerow(descriptive_header)

        metadata = self.metadata_gen.generate_metadata(golden_record, columns)

        csv_path = Path(output_path)
        metadata_path = csv_path.parent / f"{csv_path.stem}_metadata.json"
        self.metadata_gen.save_metadata(metadata, str(metadata_path))

        return str(output_path), str(metadata_path)

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

        present_elements = {e["element_id"] for e in elements}

        if "homeAddress" in present_elements:
            for extra in self.EXTRA_GOLDEN_ONLY_FIELDS:
                if not any(col["full_id"] == extra["full_id"] for col in columns):
                    columns.append(extra.copy())

        has_multiple_countries = self.target_countries and len(self.target_countries) > 1

        translated_labels = self._get_translated_labels(
            columns,
            language_code,
            has_multiple_countries
        )

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

    def _get_translated_labels(
            self,
            columns: List[Dict],
            language_code: str,
            has_multiple_countries: bool = False
    ) -> Dict[str, str]:

        field_groups = self._group_fields_by_base_key(columns)
        labels_dict = {}

        for base_key, field_variants in field_groups.items():

            if self._is_non_country_specific_field(field_variants):
                self._add_simple_label(field_variants, language_code, labels_dict)
            elif self._should_use_multi_country_format(has_multiple_countries, field_variants):
                self._add_multi_country_label(field_variants, language_code, labels_dict)
            else:
                self._add_single_country_label(field_variants, language_code, labels_dict)

        return labels_dict

    def _group_fields_by_base_key(self, columns: List[Dict]) -> Dict[str, List[Dict]]:
        field_groups = {}

        for column in columns:
            base_key = column["full_id"]

            if base_key not in field_groups:
                field_groups[base_key] = []

            field_groups[base_key].append({
                "full_id": column["full_id"],
                "country": column.get("country_code"),
                "node": column["node"],
                "is_country_specific": column.get("is_country_specific", False),
                "element_id": column.get("element_id"),
                "field_id": column.get("field_id")
            })

        return field_groups

    def _is_non_country_specific_field(self, field_variants: List[Dict]) -> bool:
        return not field_variants[0]["is_country_specific"]

    def _should_use_multi_country_format(
            self,
            has_multiple_countries: bool,
            field_variants: List[Dict]
    ) -> bool:
        return has_multiple_countries and len(field_variants) > 1

    def _add_simple_label(
            self,
            field_variants: List[Dict],
            language_code: str,
            labels_dict: Dict[str, str]
    ) -> None:
        column = field_variants[0]
        label = self._resolve_field_label(column["node"], language_code, column["full_id"])
        labels_dict[column["full_id"]] = label

    def _add_multi_country_label(
            self,
            field_variants: List[Dict],
            language_code: str,
            labels_dict: Dict[str, str]
    ) -> None:

        country_labels = []

        for variant in sorted(field_variants, key=lambda x: x["country"] or ""):
            country_code = variant["country"]
            label = self._resolve_field_label(variant["node"], language_code, variant["full_id"])
            country_labels.append(f"{country_code}: {label}")

        final_label = " | ".join(country_labels)

        for variant in field_variants:
            labels_dict[variant["full_id"]] = final_label

    def _add_single_country_label(
            self,
            field_variants: List[Dict],
            language_code: str,
            labels_dict: Dict[str, str]
    ) -> None:

        for variant in field_variants:
            label = self._resolve_field_label(variant["node"], language_code, variant["full_id"])

            # Solo añadir prefijo si hay múltiples países seleccionados
            single_country_mode = self.target_countries and len(self.target_countries) == 1

            if variant["is_country_specific"] and variant["country"] and not single_country_mode:
                final_label = f"{variant['country']}: {label}"
            else:
                final_label = label

            labels_dict[variant["full_id"]] = final_label

    def _resolve_field_label(
            self,
            field_node: Dict,
            language_code: str,
            full_field_id: str
    ) -> str:

        field_labels = field_node.get("labels", {})
        label, _ = self.language_resolver.resolve_label(field_labels, language_code)

        if not label:
            parts = full_field_id.split("_")
            label = parts[-1] if parts else full_field_id

        return label