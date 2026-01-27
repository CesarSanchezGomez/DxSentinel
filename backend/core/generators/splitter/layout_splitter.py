# backend/core/generators/golden_record/layout_splitter.py

from typing import Dict, List, Set
import csv
import json
from pathlib import Path
from backend.core.generators.golden_record.exceptions import GoldenRecordError


class LayoutSplitter:
    """
    Splits Golden Record CSV into individual SAP SuccessFactors HRIS layout templates.
    """

    # =====================================================
    # HRIS CANONICAL ELEMENT LIST
    # =====================================================
    HRIS_ELEMENTS: Set[str] = {
        "personInfo",
        "personalInfo",
        "globalInfo",
        "nationalIdCard",
        "homeAddress",
        "phoneInfo",
        "emailInfo",
        "imInfo",
        "emergencyContactPrimary",
        "personRelationshipInfo",
        "directDeposit",
        "paymentInfo",
        "employmentInfo",
        "jobInfo",
        "compInfo",
        "payComponentRecurring",
        "payComponentNonRecurring",
        "jobRelationsInfo",
        "workPermitInfo",
        "globalAssignmentInfo",
        "pensionPayoutsInfo",
        "userAccountInfo"
    }

    # =====================================================
    # INIT
    # =====================================================
    def __init__(self, metadata_path: str):
        self.metadata = self._load_metadata(metadata_path)

        self.key_mappings = self.metadata.get("key_mappings", {})
        self.layout_config = {
            k: v for k, v in self.metadata.get("layout_split_config", {}).items()
            if k in self.HRIS_ELEMENTS
        }
        self.field_catalog = self.metadata.get("field_catalog", {})

    # =====================================================
    # METADATA LOADING
    # =====================================================
    def _load_metadata(self, metadata_path: str) -> Dict:
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise GoldenRecordError(f"Error loading metadata: {str(e)}") from e

    # =====================================================
    # PUBLIC API
    # =====================================================
    def split_golden_record(self, golden_record_path: str, output_dir: str) -> List[str]:
        """
        Splits Golden Record into individual HRIS layout CSVs.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        golden_data = self._read_golden_record(golden_record_path)
        generated_files = []

        for element_id, config in self.layout_config.items():
            layout_file = self._generate_layout(
                element_id=element_id,
                config=config,
                golden_data=golden_data,
                output_dir=output_path
            )
            if layout_file:
                generated_files.append(layout_file)

        return generated_files

    # =====================================================
    # GOLDEN RECORD READER
    # =====================================================
    def _read_golden_record(self, csv_path: str) -> Dict:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            technical_header = next(reader)
            descriptive_header = next(reader)
            data_rows = list(reader)

        return {
            "technical_header": technical_header,
            "descriptive_header": descriptive_header,
            "data_rows": data_rows
        }

    # =====================================================
    # LAYOUT GENERATION
    # =====================================================
    def _generate_layout(
        self,
        element_id: str,
        config: Dict,
        golden_data: Dict,
        output_dir: Path
    ) -> str:

        element_fields = config.get("fields", [])
        key_mapping = self.key_mappings.get(element_id, {})

        technical_indices: List[int] = []
        technical_cols: List[str] = []
        descriptive_cols: List[str] = []

        # -------------------------------------------------
        # 1. KEY COLUMN (PRIMARY / FOREIGN)
        # -------------------------------------------------
        key_column = key_mapping.get("golden_column")
        layout_key = key_mapping.get("key_field")
        key_source = key_mapping.get("key_source")

        if key_column and key_column in golden_data["technical_header"]:
            key_idx = golden_data["technical_header"].index(key_column)
            technical_indices.append(key_idx)

            if key_source == "foreign":
                ref_element = key_mapping.get("references", "personInfo")
                technical_cols.append(f"{ref_element}.{layout_key}")
            else:
                technical_cols.append(layout_key)

            descriptive_cols.append(golden_data["descriptive_header"][key_idx])

        # -------------------------------------------------
        # 2. ELEMENT FIELDS
        # -------------------------------------------------
        for full_field_id in element_fields:
            if full_field_id not in golden_data["technical_header"]:
                continue

            idx = golden_data["technical_header"].index(full_field_id)
            if idx in technical_indices:
                continue

            technical_indices.append(idx)

            # SAP format: sin prefijo del elemento
            # jobInfo_holiday-calendar-code -> holiday-calendar-code
            field_name = full_field_id.split("_", 1)[1] if "_" in full_field_id else full_field_id
            technical_cols.append(field_name)
            descriptive_cols.append(golden_data["descriptive_header"][idx])

        # -------------------------------------------------
        # 3. SAP STANDARD COLUMNS
        # -------------------------------------------------
        sap_cols = self._get_sap_standard_columns(element_id)
        technical_cols.extend(sap_cols["technical"])
        descriptive_cols.extend(sap_cols["descriptive"])

        if not technical_cols:
            return None

        # -------------------------------------------------
        # 4. WRITE CSV
        # -------------------------------------------------
        layout_path = output_dir / config["layout_filename"]

        with open(layout_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(technical_cols)
            writer.writerow(descriptive_cols)

            for row in golden_data["data_rows"]:
                layout_row = [row[i] if i < len(row) else "" for i in technical_indices]
                layout_row.extend([""] * len(sap_cols["technical"]))
                writer.writerow(layout_row)

        return str(layout_path)

    # =====================================================
    # SAP STANDARD COLUMNS
    # =====================================================
    def _get_sap_standard_columns(self, element_id: str) -> Dict[str, List[str]]:
        """
        Returns SAP-required standard columns per HRIS element.
        """

        default_cols = {
            "technical": ["operation"],
            "descriptive": ["Operation"]
        }

        element_specific = {
            "personalInfo": {
                "technical": ["end-date", "attachment-id", "operation"],
                "descriptive": ["End Date", "Attachment", "Operation"]
            },
            "employmentInfo": {
                "technical": ["attachment-id", "operation"],
                "descriptive": ["Attachment", "Operation"]
            },
            "jobInfo": {
                "technical": ["end-date", "attachment-id", "operation"],
                "descriptive": ["End Date", "Attachment", "Operation"]
            },
            "phoneInfo": {
                "technical": ["start-date", "end-date", "operation"],
                "descriptive": ["Event Date", "End Date", "Operation"]
            },
            "emailInfo": {
                "technical": ["start-date", "end-date", "operation"],
                "descriptive": ["Event Date", "End Date", "Operation"]
            },
            "homeAddress": {
                "technical": ["end-date", "operation"],
                "descriptive": ["End Date", "Operation"]
            },
            "nationalIdCard": {
                "technical": ["start-date", "end-date", "notes", "operation"],
                "descriptive": ["Event Date", "End Date", "Notes", "Operation"]
            },
            "emergencyContactPrimary": {
                "technical": ["start-date", "end-date", "operation"],
                "descriptive": ["Event Date", "End Date", "Operation"]
            },
            "personRelationshipInfo": {
                "technical": [
                    "start-date",
                    "end-date",
                    "related-person-id-external",
                    "attachment-id",
                    "operation"
                ],
                "descriptive": [
                    "Event Date",
                    "End Date",
                    "Related Person Id External",
                    "Attachments",
                    "Operation"
                ]
            },
            "compInfo": {
                "technical": ["start-date", "end-date", "operation"],
                "descriptive": ["Event Date", "End Date", "Operation"]
            },
            "payComponentRecurring": {
                "technical": ["start-date", "end-date", "operation"],
                "descriptive": ["Event Date", "End Date", "Operation"]
            },
            "payComponentNonRecurring": {
                "technical": ["operation"],
                "descriptive": ["Operation"]
            },
            "workPermitInfo": {
                "technical": ["start-date", "notes", "operation"],
                "descriptive": ["Event Date", "Notes", "Operation"]
            },
            "globalAssignmentInfo": {
                "technical": ["actual-end-date", "operation"],
                "descriptive": ["Actual End Date", "Operation"]
            }
        }

        return element_specific.get(element_id, default_cols)
