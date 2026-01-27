from typing import Dict, List, Set
import re
import json


class MetadataGenerator:
    """
    Generates metadata JSON for Golden Record mapping
    based on SAP SuccessFactors HRIS elements.
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
    # KEY DETECTION PATTERNS
    # =====================================================
    PRIMARY_KEY_PATTERNS = [
        r".*-id-external$",
        r"^person-id$",
        r"^user-id$",
        r"^worker$",
        r"^employee-id$",
        r"^payroll-id$",
        r"^seq-number$"
    ]

    FOREIGN_KEY_PATTERNS = [
        r"^personInfo\.",
        r"^employmentInfo\.",
        r"^jobInfo\.",
        r"\.person-id.*",
        r"\.user-id.*",
        r"\.worker.*"
    ]

    # =====================================================
    # SAP SF KNOWN KEY MODEL
    # =====================================================
    KNOWN_KEY_MAPPINGS = {
        "personInfo": {
            "primary_keys": ["person-id-external", "user-id"],
            "is_master": True
        },
        "personalInfo": {
            "foreign_keys": ["personInfo.person-id-external"]
        },
        "globalInfo": {
            "foreign_keys": ["personInfo.person-id-external"]
        },
        "nationalIdCard": {
            "foreign_keys": ["personInfo.person-id-external"]
        },
        "homeAddress": {
            "foreign_keys": ["personInfo.person-id-external"]
        },
        "phoneInfo": {
            "foreign_keys": ["personInfo.person-id-external"]
        },
        "emailInfo": {
            "foreign_keys": ["personInfo.person-id-external"]
        },
        "imInfo": {
            "foreign_keys": ["personInfo.person-id-external"]
        },
        "emergencyContactPrimary": {
            "foreign_keys": ["personInfo.person-id-external"]
        },
        "personRelationshipInfo": {
            "foreign_keys": ["personInfo.person-id-external"]
        },
        "employmentInfo": {
            "primary_keys": ["person-id-external"]
        },
        "jobInfo": {
            "primary_keys": ["worker"],
            "alias_of": "person-id-external"
        },
        "compInfo": {
            "primary_keys": ["worker"],
            "alias_of": "person-id-external"
        },
        "payComponentRecurring": {
            "foreign_keys": ["jobInfo.worker"]
        },
        "payComponentNonRecurring": {
            "foreign_keys": ["jobInfo.worker"]
        },
        "jobRelationsInfo": {
            "foreign_keys": ["jobInfo.worker"]
        },
        "globalAssignmentInfo": {
            "foreign_keys": ["jobInfo.worker"]
        },
        "directDeposit": {
            "foreign_keys": ["employmentInfo.person-id-external"]
        },
        "paymentInfo": {
            "foreign_keys": ["employmentInfo.person-id-external"]
        },
        "pensionPayoutsInfo": {
            "foreign_keys": ["employmentInfo.person-id-external"]
        },
        "workPermitInfo": {
            "foreign_keys": ["personInfo.person-id-external"]
        },
        "userAccountInfo": {
            "primary_keys": ["user-id"],
            "alias_of": "person-id-external"
        }
    }

    # =====================================================
    # INIT
    # =====================================================
    def __init__(self):
        self.primary_patterns = [re.compile(p, re.IGNORECASE) for p in self.PRIMARY_KEY_PATTERNS]
        self.foreign_patterns = [re.compile(p, re.IGNORECASE) for p in self.FOREIGN_KEY_PATTERNS]

    # =====================================================
    # MAIN GENERATOR
    # =====================================================
    def generate_metadata(self, processed_data: Dict, columns: List[Dict]) -> Dict:
        elements = [
            e for e in processed_data.get("elements", [])
            if e.get("element_id") in self.HRIS_ELEMENTS
        ]

        metadata = {
            "version": "1.0.0",
            "elements": {},
            "field_catalog": {},
            "key_mappings": {},
            "layout_split_config": {}
        }

        for element in elements:
            meta = self._analyze_element(element)
            metadata["elements"][element["element_id"]] = meta

        metadata["field_catalog"] = self._build_field_catalog(columns, metadata["elements"])
        metadata["key_mappings"] = self._build_key_mappings(metadata["elements"])
        metadata["layout_split_config"] = self._build_layout_split_config(
            metadata["elements"],
            metadata["field_catalog"]
        )

        return metadata

    # =====================================================
    # ELEMENT ANALYSIS
    # =====================================================
    def _analyze_element(self, element: Dict) -> Dict:
        element_id = element["element_id"]
        fields = element["fields"]

        known = self.KNOWN_KEY_MAPPINGS.get(element_id, {})

        detected_primary = []
        detected_foreign = []

        for field in fields:
            fid = field["field_id"]
            full = field["full_field_id"]

            if self._is_primary_key(fid):
                detected_primary.append({"field": fid, "full": full})

            if self._is_foreign_key(fid):
                detected_foreign.append({"field": fid, "full": full})

        primary = known.get("primary_keys", [])
        foreign = known.get("foreign_keys", [])

        if not primary and not foreign:
            primary = [k["field"] for k in detected_primary]
            foreign = [k["field"] for k in detected_foreign]

        return {
            "element_id": element_id,
            "is_master": known.get("is_master", False),
            "has_own_keys": bool(primary),
            "primary_keys": primary,
            "foreign_keys": foreign,
            "alias_of": known.get("alias_of"),
            "field_count": len(fields),
            "notes": self._generate_notes(primary, foreign)
        }

    # =====================================================
    # KEY HELPERS
    # =====================================================
    def _is_primary_key(self, field_id: str) -> bool:
        return any(p.match(field_id) for p in self.primary_patterns)

    def _is_foreign_key(self, field_id: str) -> bool:
        return any(p.match(field_id) for p in self.foreign_patterns)

    # =====================================================
    # FIELD CATALOG
    # =====================================================
    def _build_field_catalog(self, columns: List[Dict], elements_meta: Dict) -> Dict:
        catalog = {}

        for col in columns:
            elem = col["element_id"]
            if elem not in elements_meta:
                continue

            fid = col["field_id"]
            full = col["full_id"]
            meta = elements_meta[elem]

            catalog[full] = {
                "element": elem,
                "field": fid,
                "is_primary_key": fid in meta["primary_keys"],
                "is_foreign_key": fid in meta["foreign_keys"],
                "is_key": fid in meta["primary_keys"] or fid in meta["foreign_keys"],
                "data_type": self._infer_data_type(fid)
            }

        return catalog

    # =====================================================
    # KEY MAPPINGS
    # =====================================================
    def _build_key_mappings(self, elements_meta: Dict) -> Dict:
        mappings = {}

        master = "personInfo"
        master_key = elements_meta[master]["primary_keys"][0]

        for eid, meta in elements_meta.items():
            if meta["has_own_keys"]:
                pk = meta["primary_keys"][0]
                mappings[eid] = {
                    "key_source": "own",
                    "key_field": pk,
                    "golden_column": f"{eid}_{pk}"
                }
            else:
                fk = meta["foreign_keys"][0] if meta["foreign_keys"] else master_key
                if "." in fk:
                    ref_elem, ref_field = fk.split(".", 1)
                else:
                    ref_elem, ref_field = master, master_key

                mappings[eid] = {
                    "key_source": "foreign",
                    "key_field": ref_field,
                    "golden_column": f"{ref_elem}_{ref_field}",
                    "references": ref_elem
                }

        return mappings

    # =====================================================
    # LAYOUT SPLIT CONFIG
    # =====================================================
    def _build_layout_split_config(self, elements_meta: Dict, field_catalog: Dict) -> Dict:
        config = {}

        for eid in elements_meta:
            fields = [
                f for f, meta in field_catalog.items()
                if meta["element"] == eid
            ]

            config[eid] = {
                "element_id": eid,
                "fields": fields,
                "field_count": len(fields),
                "layout_filename": f"{eid}_template.csv",
                "requires_foreign_key": not elements_meta[eid]["has_own_keys"]
            }

        return config

    # =====================================================
    # UTILITIES
    # =====================================================
    def _infer_data_type(self, field_id: str) -> str:
        f = field_id.lower()
        if "date" in f:
            return "date"
        if "id" in f or "code" in f:
            return "string"
        if "number" in f or "seq" in f:
            return "integer"
        return "string"

    def _generate_notes(self, pk: List, fk: List) -> str:
        if pk:
            return f"Own key: {', '.join(pk)}"
        if fk:
            return f"Uses foreign key: {', '.join(fk)}"
        return "Fallback to master key"

    def save_metadata(self, metadata: Dict, output_path: str) -> str:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return output_path
