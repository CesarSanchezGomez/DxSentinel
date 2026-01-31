from typing import Dict, List
import json
from datetime import datetime
from backend.core.generators.metadata.business_key_resolver import BusinessKeyResolver
from backend.core.generators.metadata.field_identifier_extractor import FieldIdentifierExtractor
from backend.core.generators.metadata.field_categorizer import FieldCategorizer


class MetadataGenerator:
    SAP_BUSINESS_KEYS = {
        "personInfo": {
            "keys": ["personIdExternal"],
            "sap_format": ["user-id"],
            "is_master": True,
            "description": "Master entity - uses user-id as primary key"
        },
        "personalInfo": {
            "keys": ["personIdExternal", "startDate"],
            "sap_format": ["personInfo.person-id-external", "start-date"],
            "is_master": False,
            "references": "personInfo"
        },
        "globalInfo": {
            "keys": ["personIdExternal", "startDate", "country"],
            "sap_format": ["personInfo.person-id-external", "start-date", "country"],
            "is_master": False,
            "references": "personInfo"
        },
        "nationalIdCard": {
            "keys": ["personIdExternal", "country", "cardType"],
            "sap_format": ["personInfo.person-id-external", "country", "card-type"],
            "is_master": False,
            "references": "personInfo"
        },
        "homeAddress": {
            "keys": ["personIdExternal", "effectiveStartDate", "addressType"],
            "sap_format": ["personInfo.person-id-external", "start-date", "address-type"],
            "is_master": False,
            "references": "personInfo"
        },
        "phoneInfo": {
            "keys": ["personIdExternal", "phoneType"],
            "sap_format": ["personInfo.person-id-external", "phone-type"],
            "is_master": False,
            "references": "personInfo"
        },
        "emailInfo": {
            "keys": ["personIdExternal", "emailType"],
            "sap_format": ["personInfo.person-id-external", "email-type"],
            "is_master": False,
            "references": "personInfo"
        },
        "imInfo": {
            "keys": ["personIdExternal", "domain"],
            "sap_format": ["personInfo.person-id-external", "domain"],
            "is_master": False,
            "references": "personInfo"
        },
        "emergencyContactPrimary": {
            "keys": ["personIdExternal", "name", "relationship"],
            "sap_format": ["personInfo.person-id-external", "name", "relationship"],
            "is_master": False,
            "references": "personInfo"
        },
        "personRelationshipInfo": {
            "keys": ["personIdExternal", "relatedPersonIdExternal", "startDate"],
            "sap_format": ["personInfo.person-id-external", "related-person-id-external", "start-date"],
            "is_master": False,
            "references": "personInfo"
        },
        "employmentInfo": {
            "keys": ["personIdExternal", "userId"],
            "sap_format": ["person-id-external", "user-id"],
            "is_master": False,
            "references": "personInfo"
        },
        "jobInfo": {
            "keys": ["userId", "startDate", "seqNumber"],
            "sap_format": ["user-id", "start-date", "seq-number"],
            "is_master": False,
            "references": "employmentInfo"
        },
        "compInfo": {
            "keys": ["userId", "startDate", "seqNumber"],
            "sap_format": ["user-id", "start-date", "seq-number"],
            "is_master": False,
            "references": "employmentInfo"
        },
        "payComponentRecurring": {
            "keys": ["userId", "payComponent", "startDate", "seqNumber"],
            "sap_format": ["user-id", "pay-component", "start-date", "seq-number"],
            "is_master": False,
            "references": "employmentInfo"
        },
        "payComponentNonRecurring": {
            "keys": ["userId", "payComponentCode", "payDate"],
            "sap_format": ["user-id", "pay-component-code", "pay-date"],
            "is_master": False,
            "references": "employmentInfo"
        },
        "jobRelationsInfo": {
            "keys": ["userId", "relationshipType", "startDate"],
            "sap_format": ["user-id", "relationship-type", "start-date"],
            "is_master": False,
            "references": "employmentInfo"
        },
        "workPermitInfo": {
            "keys": ["userId", "country", "documentType", "documentNumber", "issueDate"],
            "sap_format": ["user-id", "country", "document-type", "document-number", "issue-date"],
            "is_master": False,
            "references": "employmentInfo"
        },
        "globalAssignmentInfo": {
            "keys": ["userId"],
            "sap_format": ["user-id"],
            "is_master": False,
            "references": "employmentInfo"
        },
        "pensionPayoutsInfo": {
            "keys": ["userId"],
            "sap_format": ["user-id"],
            "is_master": False,
            "references": "employmentInfo"
        }
    }

    def __init__(self):
        self.key_resolver = BusinessKeyResolver()
        self.field_extractor = FieldIdentifierExtractor()
        self.field_categorizer = FieldCategorizer(self.SAP_BUSINESS_KEYS)

    def generate_metadata(self, processed_data: Dict, columns: List[Dict]) -> Dict:

        elements = processed_data.get("elements", [])
        available_headers = [col["full_id"] for col in columns]

        metadata = {
            "version": "2.0.0",
            "generated_at": self._get_timestamp(),
            "elements": {},
            "field_catalog": {},
            "business_keys": {},
            "layout_split_config": {}
        }

        for element in elements:
            element_id = element["element_id"]
            element_metadata = self._analyze_element(element, columns)
            metadata["elements"][element_id] = element_metadata

        metadata["field_catalog"] = self._build_field_catalog(columns, metadata["elements"])
        metadata["business_keys"] = self._build_business_keys_mapping(
            metadata["elements"],
            available_headers
        )
        metadata["layout_split_config"] = self._build_layout_split_config(
            metadata["elements"],
            metadata["field_catalog"],
            metadata["business_keys"],
            columns
        )

        return metadata

    def _analyze_element(self, element: Dict, all_columns: List[Dict]) -> Dict:

        element_id = element["element_id"]
        fields = element["fields"]

        sap_config = self.SAP_BUSINESS_KEYS.get(element_id, {})

        return {
            "element_id": element_id,
            "is_master": sap_config.get("is_master", False),
            "business_keys": sap_config.get("keys", []),
            "sap_format_keys": sap_config.get("sap_format", []),
            "references": sap_config.get("references"),
            "field_count": len(fields),
            "description": sap_config.get("description", f"Standard {element_id} entity")
        }

    def _build_field_catalog(self, columns: List[Dict], elements_meta: Dict) -> Dict:

        catalog = {}

        for column in columns:
            full_field_id = column["full_id"]
            element_id = column["element_id"]
            field_id = column["field_id"]

            element_meta = elements_meta.get(element_id, {})

            is_business_key = self.field_categorizer.is_business_key(element_id, field_id)
            is_hris = self.field_categorizer.is_hris_field(element_id, field_id)

            catalog[full_field_id] = {
                "element": element_id,
                "field": field_id,
                "is_business_key": is_business_key,
                "is_hris_field": is_hris,
                "data_type": self._infer_data_type(field_id),
                "category": self._categorize_field(field_id)
            }

        return catalog

    def _build_business_keys_mapping(
            self,
            elements_meta: Dict,
            available_columns: List[str]
    ) -> Dict:
        mappings = {}

        for elem_id, meta in elements_meta.items():
            business_keys = meta.get("business_keys", [])
            sap_format_keys = meta.get("sap_format_keys", [])
            references = meta.get("references")

            if not business_keys:
                continue

            key_mappings = []
            for golden_key, sap_key in zip(business_keys, sap_format_keys):
                golden_column = self.key_resolver.resolve_golden_column(
                    sap_key,
                    None,
                    available_columns,
                    elem_id
                )

                if golden_column:
                    key_mappings.append({
                        "golden_column": golden_column,
                        "sap_column": sap_key,
                        "field_name": golden_key,
                        "is_foreign": "." in sap_key
                    })

            mappings[elem_id] = {
                "business_keys": key_mappings,
                "references": references,
                "is_master": meta.get("is_master", False)
            }

        return mappings

    def _build_layout_split_config(
            self,
            elements_meta: Dict,
            field_catalog: Dict,
            business_keys: Dict,
            all_columns: List[Dict]
    ) -> Dict:

        config = {}
        grouped_by_entity = {}

        for column in all_columns:
            full_field_id = column["full_id"]

            entity_id, field_id, country_code = self.field_extractor.extract_entity_and_field(
                full_field_id
            )

            suffix = self.field_extractor.should_split_by_suffix(entity_id, field_id)

            if suffix:
                group_key = f"{entity_id}_{suffix}"
            else:
                group_key = entity_id

            if group_key not in grouped_by_entity:
                grouped_by_entity[group_key] = []

            grouped_by_entity[group_key].append(full_field_id)

        for group_key, fields in grouped_by_entity.items():
            if "_" in group_key and group_key.split("_")[0] in self.field_extractor.SPECIAL_PREFIXES:
                entity_id = group_key.split("_")[0]
                suffix = group_key.split("_", 1)[1]
                filename = f"{group_key}_template.csv"
            else:
                entity_id = group_key
                filename = f"{entity_id}_template.csv"

            business_key_config = business_keys.get(entity_id, {})

            config[group_key] = {
                "element_id": entity_id,
                "group_key": group_key,
                "fields": fields,
                "field_count": len(fields),
                "business_keys": business_key_config.get("business_keys", []),
                "layout_filename": filename
            }

        return config

    def _infer_data_type(self, field_id: str) -> str:

        field_lower = field_id.lower()

        if "date" in field_lower:
            return "date"
        elif "id" in field_lower or "code" in field_lower:
            return "string"
        elif "number" in field_lower or "seq" in field_lower:
            return "integer"
        elif "rate" in field_lower or "ratio" in field_lower:
            return "decimal"
        elif "is-" in field_lower or field_lower.startswith("is"):
            return "boolean"
        else:
            return "string"

    def _categorize_field(self, field_id: str) -> str:

        field_lower = field_id.lower()

        if any(k in field_lower for k in ["id", "code", "number"]):
            return "identifier"
        elif "date" in field_lower:
            return "temporal"
        elif "custom" in field_lower or "udf" in field_lower:
            return "custom"
        elif any(k in field_lower for k in ["name", "title", "description"]):
            return "descriptive"
        else:
            return "operational"

    def _get_timestamp(self) -> str:

        return datetime.utcnow().isoformat() + 'Z'

    def save_metadata(self, metadata: Dict, output_path: str) -> str:

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return output_path
