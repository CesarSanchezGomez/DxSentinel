from typing import Dict, List, Set, Optional
import re
import json
from pathlib import Path


class MetadataGenerator:
    """Generates metadata JSON for Golden Record mapping with SAP SuccessFactors business keys."""

    # Business Keys configuration según templates oficiales de SAP SuccessFactors
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
            "keys": ["personIdExternal", "userId", "startDate"],
            "sap_format": ["person-id-external", "user-id", "start-date"],
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
            "keys": ["userId", "startDate"],
            "sap_format": ["user-id", "start-date"],
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
        pass

    def generate_metadata(self, processed_data: Dict, columns: List[Dict]) -> Dict:
        """Generates complete metadata for Golden Record."""
        elements = processed_data.get("elements", [])

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
        metadata["business_keys"] = self._build_business_keys_mapping(metadata["elements"], columns)
        metadata["layout_split_config"] = self._build_layout_split_config(
            metadata["elements"],
            metadata["field_catalog"],
            metadata["business_keys"]
        )

        return metadata

    def _analyze_element(self, element: Dict, all_columns: List[Dict]) -> Dict:
        """Analyzes an element using SAP business keys configuration."""
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
        """Builds complete field catalog."""
        catalog = {}

        for column in columns:
            full_field_id = column["full_id"]
            element_id = column["element_id"]
            field_id = column["field_id"]

            element_meta = elements_meta.get(element_id, {})
            is_business_key = field_id in element_meta.get("business_keys", [])

            catalog[full_field_id] = {
                "element": element_id,
                "field": field_id,
                "is_business_key": is_business_key,
                "data_type": self._infer_data_type(field_id),
                "category": self._categorize_field(field_id)
            }

        return catalog

    def _build_business_keys_mapping(self, elements_meta: Dict, columns: List[Dict]) -> Dict:
        """Builds business keys mapping for layout splitting."""
        mappings = {}
        available_columns = [col["full_id"] for col in columns]

        for elem_id, meta in elements_meta.items():
            business_keys = meta.get("business_keys", [])
            sap_format_keys = meta.get("sap_format_keys", [])
            references = meta.get("references")

            if not business_keys:
                continue

            key_mappings = []
            for golden_key, sap_key in zip(business_keys, sap_format_keys):
                # Determinar la columna en el Golden Record
                golden_column = self._resolve_golden_column(
                    elem_id,
                    golden_key,
                    sap_key,
                    available_columns
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

    def _resolve_golden_column(
            self,
            elem_id: str,
            golden_key: str,
            sap_key: str,
            available_columns: List[str]
    ) -> Optional[str]:
        """
        Resuelve la columna del Golden Record para una business key.

        Lógica de resolución:
        1. user-id → personInfo_person-id-external
        2. person-id-external → personInfo_person-id-external
        3. personInfo.person-id-external → personInfo_person-id-external
        4. Otros campos con referencia → buscar en el elemento referenciado
        5. Campos locales → buscar en el elemento actual
        """

        # Caso especial: user-id o person-id-external sin prefijo
        if sap_key in ["user-id", "person-id-external"]:
            if "personInfo_person-id-external" in available_columns:
                return "personInfo_person-id-external"

        # Caso: Referencias con punto (personInfo.person-id-external)
        if "." in sap_key:
            ref_elem, ref_field = sap_key.split(".", 1)
            # El Golden Record usa kebab-case, no camelCase
            golden_column = f"{ref_elem}_{ref_field}"

            if golden_column in available_columns:
                return golden_column

        # Caso: Campo local en el elemento actual
        # Intentar con el golden_key directamente
        candidate = f"{elem_id}_{golden_key}"
        if candidate in available_columns:
            return candidate

        # Intentar convertir golden_key a kebab-case si está en camelCase
        kebab_key = self._camel_to_kebab_simple(golden_key)
        candidate_kebab = f"{elem_id}_{kebab_key}"
        if candidate_kebab in available_columns:
            return candidate_kebab

        # Buscar coincidencias parciales
        for col in available_columns:
            if col.endswith(f"_{golden_key}") or col.endswith(f"_{kebab_key}"):
                return col

        return None

    def _camel_to_kebab_simple(self, camel_str: str) -> str:
        """Convierte camelCase a kebab-case de forma simple."""
        import re
        kebab = re.sub('([a-z0-9])([A-Z])', r'\1-\2', camel_str)
        return kebab.lower()

    def _sap_to_camel_case(self, sap_field: str) -> str:
        """Convierte formato SAP (kebab-case) a camelCase usado en Golden Record."""
        # Casos especiales conocidos
        special_cases = {
            "person-id-external": "personIdExternal",
            "user-id": "userId",
            "start-date": "startDate",
            "end-date": "endDate",
            "card-type": "cardType",
            "address-type": "addressType",
            "phone-type": "phoneType",
            "email-address": "emailType",
            "related-person-id-external": "relatedPersonIdExternal",
            "seq-number": "seqNumber",
            "pay-component": "payComponent",
            "pay-component-code": "payComponentCode",
            "pay-date": "payDate",
            "relationship-type": "relationshipType",
            "document-type": "documentType",
            "document-number": "documentNumber",
            "issue-date": "issueDate"
        }

        if sap_field in special_cases:
            return special_cases[sap_field]

        # Conversión genérica para otros casos
        parts = sap_field.split('-')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])

    def _build_layout_split_config(self, elements_meta: Dict, field_catalog: Dict,
                                   business_keys: Dict) -> Dict:
        """Builds configuration for splitting Golden Record into layouts."""
        config = {}

        for elem_id, meta in elements_meta.items():
            element_fields = [
                field_id for field_id, field_meta in field_catalog.items()
                if field_meta["element"] == elem_id
            ]

            business_key_config = business_keys.get(elem_id, {})

            config[elem_id] = {
                "element_id": elem_id,
                "fields": element_fields,
                "field_count": len(element_fields),
                "business_keys": business_key_config.get("business_keys", []),
                "layout_filename": f"{elem_id}_template.csv"
            }

        return config

    def _infer_data_type(self, field_id: str) -> str:
        """Infers data type from field ID."""
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
        """Categorizes field for organization."""
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
        """Gets current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'

    def save_metadata(self, metadata: Dict, output_path: str) -> str:
        """Saves metadata to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return output_path