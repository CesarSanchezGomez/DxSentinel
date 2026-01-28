from typing import Optional, Tuple
import re


class FieldIdentifierExtractor:
    SPECIAL_PREFIXES = {"workPermitInfo"}  # Cambiar de "workPermit" a "workPermitInfo"
    COUNTRY_CODE_PATTERN = re.compile(r'^([A-Z]{2,3})_(.+)$')

    def extract_entity_and_field(self, full_field_id: str) -> Tuple[str, str, Optional[str]]:
        country_code = None
        remaining = full_field_id

        match = self.COUNTRY_CODE_PATTERN.match(full_field_id)
        if match:
            country_code = match.group(1)
            remaining = match.group(2)

        parts = remaining.split('_', 1)
        if len(parts) == 2:
            entity_id = parts[0]
            field_id = parts[1]
        else:
            entity_id = parts[0]
            field_id = parts[0]

        return entity_id, field_id, country_code

    def should_split_by_suffix(self, entity_id: str, field_id: str) -> Optional[str]:
        if entity_id not in self.SPECIAL_PREFIXES:
            return None

        known_suffixes = {"RFC", "CURP", "NSS", "IMSS"}

        for suffix in known_suffixes:
            if suffix in field_id.upper():  # Buscar en mayúsculas
                return suffix

        return None