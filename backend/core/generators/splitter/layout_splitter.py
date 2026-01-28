from typing import Dict, List, Optional, Tuple
import csv
import json
from pathlib import Path
from backend.core.generators.metadata.business_key_resolver import BusinessKeyResolver
from backend.core.generators.metadata.field_identifier_extractor import FieldIdentifierExtractor

class LayoutSplitter:

    def __init__(self, metadata_path: str):
        self.metadata = self._load_metadata(metadata_path)
        self.business_keys = self.metadata.get("business_keys", {})
        self.layout_config = self.metadata.get("layout_split_config", {})
        self.field_catalog = self.metadata.get("field_catalog", {})

        self.key_resolver = BusinessKeyResolver()
        self.field_extractor = FieldIdentifierExtractor()

    def _load_metadata(self, metadata_path: str) -> Dict:

        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def split_golden_record(self, golden_record_path: str, output_dir: str) -> List[str]:

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        golden_data = self._read_golden_record(golden_record_path)
        generated_files = []

        for group_key, config in self.layout_config.items():
            layout_file = self._generate_layout(
                group_key=group_key,
                config=config,
                golden_data=golden_data,
                output_dir=output_path
            )
            if layout_file:
                generated_files.append(layout_file)

        return generated_files

    def _read_golden_record(self, csv_path: str) -> Dict:

        encodings_to_try = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']

        for encoding in encodings_to_try:
            try:
                with open(csv_path, 'r', encoding=encoding) as f:
                    reader = csv.reader(f)
                    technical_header = next(reader)
                    descriptive_header = next(reader)
                    data_rows = list(reader)

                return {
                    "technical_header": technical_header,
                    "descriptive_header": descriptive_header,
                    "data_rows": data_rows
                }
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                raise Exception(f"Error reading with {encoding}: {str(e)}")

        raise Exception(f"Unable to read file with any supported encoding")

    def _generate_layout(
            self,
            group_key: str,
            config: Dict,
            golden_data: Dict,
            output_dir: Path
    ) -> str:
        element_id = config["element_id"]
        element_fields = config["fields"]

        # CAMBIO: Obtener business keys directamente de MetadataGenerator.SAP_BUSINESS_KEYS
        from backend.core.generators.metadata.metadata_generator import MetadataGenerator

        sap_config = MetadataGenerator.SAP_BUSINESS_KEYS.get(element_id, {})
        sap_format_keys = sap_config.get("sap_format", [])

        columns = []
        added_indices = set()

        # CAMBIO: Usar sap_format_keys directamente en lugar de business_keys del metadata
        for sap_column in sap_format_keys:
            source_info = self._find_source_column(
                None,
                sap_column,
                golden_data["technical_header"],
                element_id  # NUEVO: Pasar element_id
            )

            if source_info:
                source_idx, descriptive = source_info

                golden_field_at_idx = golden_data["technical_header"][source_idx] if source_idx < len(
                    golden_data["technical_header"]) else None
                field_meta = self.field_catalog.get(golden_field_at_idx, {}) if golden_field_at_idx else {}
                is_hris_field = field_meta.get("is_hris_field", False)

                if is_hris_field:
                    descriptive = self._generate_descriptive_name(sap_column)
                elif source_idx < len(golden_data["descriptive_header"]):
                    descriptive = golden_data["descriptive_header"][source_idx]

                columns.append({
                    "sap_name": sap_column,
                    "source_idx": source_idx,
                    "descriptive": descriptive,
                    "is_business_key": True
                })

                if not is_hris_field:
                    added_indices.add(source_idx)

        for field_id in element_fields:
            if field_id in golden_data["technical_header"]:
                idx = golden_data["technical_header"].index(field_id)

                if idx not in added_indices:
                    field_meta = self.field_catalog.get(field_id, {})

                    is_business_key_current = field_meta.get("is_business_key", False)
                    is_hris_field = field_meta.get("is_hris_field", False)

                    if is_business_key_current and not is_hris_field:
                        continue

                    entity_id, extracted_field, country_code = self.field_extractor.extract_entity_and_field(
                        field_id
                    )

                    suffix = self.field_extractor.should_split_by_suffix(entity_id, extracted_field)
                    if suffix and suffix in group_key:
                        extracted_field = extracted_field.replace(suffix, "").replace("_", "").strip("-")
                        if not extracted_field:
                            continue

                    columns.append({
                        "sap_name": extracted_field,
                        "source_idx": idx,
                        "descriptive": golden_data["descriptive_header"][idx],
                        "is_business_key": False
                    })
                    added_indices.add(idx)

        if not columns:
            return None

        layout_path = output_dir / config["layout_filename"]

        with open(layout_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)

            technical_header = [col["sap_name"] for col in columns]
            descriptive_header = [col["descriptive"] for col in columns]

            writer.writerow(technical_header)
            writer.writerow(descriptive_header)

            for row in golden_data["data_rows"]:
                output_row = []
                for col in columns:
                    idx = col["source_idx"]
                    value = row[idx] if idx < len(row) else ""
                    output_row.append(value)

                writer.writerow(output_row)

        return str(layout_path)

    def _find_source_column(
            self,
            golden_column: Optional[str],
            sap_column: str,
            available_headers: List[str],
            element_id: Optional[str] = None  # NUEVO parámetro
    ) -> Optional[Tuple[int, str]]:
        resolved = self.key_resolver.resolve_golden_column(
            sap_column,
            golden_column,
            available_headers,
            element_id  # NUEVO: Pasar element_id al resolver
        )

        if resolved and resolved in available_headers:
            idx = available_headers.index(resolved)
            descriptive = self._generate_descriptive_name(sap_column)
            return (idx, descriptive)

        return None

    def _generate_descriptive_name(self, sap_column: str) -> str:

        descriptive_map = {
            "user-id": "User ID",
            "person-id-external": "Person ID External",
            "personInfo.person-id-external": "Person ID External",
            "start-date": "Start Date",
            "end-date": "End Date",
            "seq-number": "Sequence Number",
            "pay-component": "Pay Component",
            "email-address": "Email Address",
            "phone-type": "Phone Type",
            "card-type": "Card Type",
            "address-type": "Address Type",
            "country": "Country",
            "relationship": "Relationship",
            "name": "Name",
            "domain": "Domain",
            "document-type": "Document Type",
            "document-number": "Document Number",
            "issue-date": "Issue Date"
        }

        return descriptive_map.get(sap_column, sap_column.replace("-", " ").title())