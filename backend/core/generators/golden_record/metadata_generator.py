from typing import Dict, List, Set, Optional
import re
import json
from pathlib import Path


class MetadataGenerator:
    """Generates metadata JSON for Golden Record mapping."""

    # Patrones para detectar diferentes tipos de keys
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
        r"\.person-id.*",
        r"\.user-id.*"
    ]

    # Mapping conocido de qué key usa cada elemento
    KNOWN_KEY_MAPPINGS = {
        "personInfo": {
            "primary_keys": ["person-id-external", "user-id"],
            "is_master": True
        },
        "personalInfo": {
            "foreign_keys": ["personInfo.person-id-external"],
            "is_master": False
        },
        "employmentInfo": {
            "primary_keys": ["person-id-external"],
            "is_master": False
        },
        "jobInfo": {
            "primary_keys": ["worker"],
            "alias_of": "person-id-external",
            "is_master": False
        },
        "compInfo": {
            "primary_keys": ["worker"],
            "alias_of": "person-id-external",
            "is_master": False
        },
        "phoneInfo": {
            "foreign_keys": ["personInfo.person-id-external"],
            "is_master": False
        },
        "emailInfo": {
            "foreign_keys": ["personInfo.person-id-external"],
            "is_master": False
        },
        "homeAddress": {
            "foreign_keys": ["personInfo.person-id-external"],
            "is_master": False
        },
        "nationalIdCard": {
            "foreign_keys": ["personInfo.person-id-external"],
            "is_master": False
        },
        "emergencyContactPrimary": {
            "primary_keys": ["person-id-external"],
            "is_master": False
        }
    }

    def __init__(self):
        self.primary_patterns = [re.compile(p, re.IGNORECASE) for p in self.PRIMARY_KEY_PATTERNS]
        self.foreign_patterns = [re.compile(p, re.IGNORECASE) for p in self.FOREIGN_KEY_PATTERNS]

    def generate_metadata(self, processed_data: Dict, columns: List[Dict]) -> Dict:
        """
        Generates complete metadata for Golden Record.

        Args:
            processed_data: Output from ElementProcessor
            columns: Columns list from CSVGenerator

        Returns:
            Complete metadata dictionary
        """
        elements = processed_data.get("elements", [])

        metadata = {
            "version": "1.0.0",
            "generated_at": self._get_timestamp(),
            "elements": {},
            "field_catalog": {},
            "key_mappings": {},
            "layout_split_config": {}
        }

        # Procesar cada elemento
        for element in elements:
            element_id = element["element_id"]
            element_metadata = self._analyze_element(element, columns)
            metadata["elements"][element_id] = element_metadata

        # Construir catálogo de campos
        metadata["field_catalog"] = self._build_field_catalog(columns, metadata["elements"])

        # Generar configuración de mapeo de keys
        metadata["key_mappings"] = self._build_key_mappings(metadata["elements"])

        # Configuración para split de layouts
        metadata["layout_split_config"] = self._build_layout_split_config(
            metadata["elements"],
            metadata["field_catalog"]
        )

        return metadata

    def _analyze_element(self, element: Dict, all_columns: List[Dict]) -> Dict:
        """Analyzes an element to detect its keys and characteristics."""
        element_id = element["element_id"]
        fields = element["fields"]

        # Obtener configuración conocida si existe
        known_config = self.KNOWN_KEY_MAPPINGS.get(element_id, {})

        # Detectar primary keys
        detected_primary = []
        detected_foreign = []

        for field in fields:
            field_id = field["field_id"]
            full_field_id = field["full_field_id"]

            # Verificar si es primary key
            if self._is_primary_key(field_id):
                detected_primary.append({
                    "field_id": field_id,
                    "full_field_id": full_field_id,
                    "detection_method": "pattern"
                })

            # Verificar si es foreign key
            if self._is_foreign_key(field_id):
                detected_foreign.append({
                    "field_id": field_id,
                    "full_field_id": full_field_id,
                    "detection_method": "pattern"
                })

        # Combinar con configuración conocida
        final_primary = known_config.get("primary_keys", [])
        final_foreign = known_config.get("foreign_keys", [])

        # Si no hay configuración conocida, usar detección
        if not final_primary and not final_foreign:
            final_primary = [k["field_id"] for k in detected_primary]
            final_foreign = [k["field_id"] for k in detected_foreign]

        return {
            "element_id": element_id,
            "has_own_keys": len(final_primary) > 0,
            "is_master": known_config.get("is_master", len(final_primary) > 0),
            "primary_keys": final_primary,
            "foreign_keys": final_foreign,
            "detected_keys": {
                "primary": detected_primary,
                "foreign": detected_foreign
            },
            "field_count": len(fields),
            "alias_of": known_config.get("alias_of"),
            "notes": self._generate_notes(element_id, final_primary, final_foreign)
        }

    def _is_primary_key(self, field_id: str) -> bool:
        """Checks if field matches primary key patterns."""
        for pattern in self.primary_patterns:
            if pattern.match(field_id):
                return True
        return False

    def _is_foreign_key(self, field_id: str) -> bool:
        """Checks if field matches foreign key patterns."""
        for pattern in self.foreign_patterns:
            if pattern.match(field_id):
                return True
        return False

    def _build_field_catalog(self, columns: List[Dict], elements_meta: Dict) -> Dict:
        """Builds complete field catalog."""
        catalog = {}

        for column in columns:
            full_field_id = column["full_id"]
            element_id = column["element_id"]
            field_id = column["field_id"]

            element_meta = elements_meta.get(element_id, {})

            is_key = (
                    field_id in element_meta.get("primary_keys", []) or
                    field_id in element_meta.get("foreign_keys", [])
            )

            catalog[full_field_id] = {
                "element": element_id,
                "field": field_id,
                "is_key": is_key,
                "is_primary_key": field_id in element_meta.get("primary_keys", []),
                "is_foreign_key": field_id in element_meta.get("foreign_keys", []),
                "data_type": self._infer_data_type(field_id),
                "category": self._categorize_field(field_id)
            }

        return catalog

    def _build_key_mappings(self, elements_meta: Dict) -> Dict:
        """Builds key mapping configuration for layout splitting."""
        mappings = {}

        # Encontrar el elemento master (usualmente personInfo)
        master_element = None
        master_key = None

        for elem_id, meta in elements_meta.items():
            if meta.get("is_master"):
                master_element = elem_id
                if meta.get("primary_keys"):
                    master_key = meta["primary_keys"][0]
                break

        # Mapear cada elemento a su key
        for elem_id, meta in elements_meta.items():
            if meta.get("has_own_keys"):
                # Usa su propia key
                primary = meta["primary_keys"][0] if meta["primary_keys"] else None
                mappings[elem_id] = {
                    "key_source": "own",
                    "key_field": primary,
                    "golden_column": f"{elem_id}_{primary}" if primary else None,
                    "layout_column": primary
                }
            else:
                # Debe usar foreign key
                foreign = meta["foreign_keys"][0] if meta["foreign_keys"] else None
                if foreign:
                    # Extraer el elemento y campo de la foreign key
                    if "." in foreign:
                        ref_element, ref_field = foreign.split(".", 1)
                        golden_col = f"{ref_element}_{ref_field}"
                    else:
                        golden_col = f"{master_element}_{master_key}"
                        ref_field = master_key

                    mappings[elem_id] = {
                        "key_source": "foreign",
                        "key_field": ref_field,
                        "golden_column": golden_col,
                        "layout_column": ref_field,
                        "references": master_element if "." not in foreign else ref_element
                    }
                else:
                    # Fallback al master key
                    mappings[elem_id] = {
                        "key_source": "fallback",
                        "key_field": master_key,
                        "golden_column": f"{master_element}_{master_key}",
                        "layout_column": master_key,
                        "references": master_element
                    }

        return mappings

    def _build_layout_split_config(self, elements_meta: Dict, field_catalog: Dict) -> Dict:
        """Builds configuration for splitting Golden Record into layouts."""
        config = {}

        for elem_id, meta in elements_meta.items():
            # Obtener campos que pertenecen a este elemento
            element_fields = [
                field_id for field_id, field_meta in field_catalog.items()
                if field_meta["element"] == elem_id
            ]

            config[elem_id] = {
                "element_id": elem_id,
                "fields": element_fields,
                "field_count": len(element_fields),
                "requires_foreign_key": not meta.get("has_own_keys"),
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

    def _generate_notes(self, element_id: str, primary_keys: List, foreign_keys: List) -> str:
        """Generates helpful notes for the element."""
        notes = []

        if primary_keys:
            notes.append(f"Uses own keys: {', '.join(primary_keys)}")

        if foreign_keys:
            notes.append(f"References: {', '.join(foreign_keys)}")

        if not primary_keys and not foreign_keys:
            notes.append("No keys detected - will use fallback master key")

        return " | ".join(notes) if notes else "Standard element"

    def _get_timestamp(self) -> str:
        """Gets current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'

    def save_metadata(self, metadata: Dict, output_path: str) -> str:
        """Saves metadata to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return output_path