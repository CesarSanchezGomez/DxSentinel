from typing import Optional, List


class BusinessKeyResolver:
    SPECIAL_KEY_MAPPINGS = {
        "user-id": "personInfo_person-id-external",
        "person-id-external": "personInfo_person-id-external",
        "personInfo.person-id-external": "personInfo_person-id-external"
    }

    COMMON_KEYS = {
        "start-date", "end-date", "country", "seq-number",
        "card-type", "phone-type", "email-type", "address-type",
        "relationship-type", "pay-component", "pay-component-code",
        "pay-date", "domain", "name", "relationship",
        "document-type", "document-number", "issue-date"
    }

    PREFIXED_KEY_PATTERNS = {
        "homeAddress": ["home_", "fiscal_"],
        "workPermitInfo": ["workPermitInfo_"]
    }

    def resolve_golden_column(
            self,
            sap_column: str,
            golden_column: Optional[str],
            available_headers: List[str],
            entity_id: Optional[str] = None
    ) -> Optional[str]:
        if golden_column and golden_column in available_headers:
            return golden_column

        if sap_column in self.SPECIAL_KEY_MAPPINGS:
            mapped = self.SPECIAL_KEY_MAPPINGS[sap_column]
            if mapped in available_headers:
                return mapped

        if "." in sap_column:
            derived = self._resolve_reference_key(sap_column, available_headers)
            if derived:
                return derived

        if entity_id:
            candidate = f"{entity_id}_{sap_column}"
            if candidate in available_headers:
                return candidate

        if entity_id and entity_id in self.PREFIXED_KEY_PATTERNS:
            for prefix in self.PREFIXED_KEY_PATTERNS[entity_id]:
                candidate = f"{prefix}{sap_column}"
                if candidate in available_headers:
                    return candidate

        if sap_column in self.COMMON_KEYS:
            return self._find_matching_suffix(sap_column, available_headers)

        return self._find_matching_suffix(sap_column, available_headers)

    def _resolve_reference_key(self, sap_column: str, available_headers: List[str]) -> Optional[str]:
        ref_element, ref_field = sap_column.split(".", 1)
        candidate = f"{ref_element}_{ref_field}"

        if candidate in available_headers:
            return candidate

        return None

    def _find_matching_suffix(self, field_name: str, available_headers: List[str]) -> Optional[str]:
        for header in available_headers:
            if header.endswith(f"_{field_name}") or header.endswith(f"-{field_name}"):
                return header

        return None