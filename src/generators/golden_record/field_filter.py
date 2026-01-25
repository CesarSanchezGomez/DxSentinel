from typing import Dict, List, Tuple, Optional
import re
from .exceptions import FieldFilterError


class FieldFilter:
    """Filters and classifies fields according to Golden Record criteria."""

    IDENTIFIER_PATTERNS = [r"id$", r"number$", r"name$", r"code$"]
    DATE_PATTERNS = [r"date$", r"Date$", r"start", r"end", r"effective"]
    CUSTOM_PATTERNS = [r"custom", r"Custom", r"udf", r"UDF"]

    def __init__(self):
        self.identifier_patterns = [re.compile(p, re.IGNORECASE) for p in self.IDENTIFIER_PATTERNS]
        self.date_patterns = [re.compile(p, re.IGNORECASE) for p in self.DATE_PATTERNS]
        self.custom_patterns = [re.compile(p, re.IGNORECASE) for p in self.CUSTOM_PATTERNS]



    def filter_field(self, field_node: Dict) -> Tuple[bool, Optional[str]]:
        """
        Determines if a field should be included in Golden Record.

        Args:
            field_node: Field node from model

        Returns:
            Tuple (include, exclusion_reason)
        """
        try:
            attributes = field_node.get("attributes", {}).get("raw", {})
            field_id = field_node.get("technical_id") or field_node.get("id", "")

            visibility = attributes.get("visibility", "").lower()
            if visibility == "none":
                return False, "visibility='none'"
            
            if self._is_internal_field(field_id, attributes):
                return False, "campo técnico interno"

            return True, None
        
            

        except Exception as e:
            raise FieldFilterError(f"Error filtering field: {str(e)}") from e

    def classify_field(self, field_id: str) -> str:
        """
        Classifies a field for internal ordering.

        Returns:
            Category: "identifier", "date", "custom", "other"
        """
        for pattern in self.custom_patterns:
            if pattern.search(field_id):
                return "custom"

        for pattern in self.identifier_patterns:
            if pattern.search(field_id):
                return "identifier"

        for pattern in self.date_patterns:
            if pattern.search(field_id):
                return "date"

        return "other"

    def sort_fields(self, fields: List[Dict]) -> List[Dict]:
        """
        Sorts fields within an element.

        Order: Identifiers → Dates → Others → Custom
        """
        classified = {
            "identifier": [],
            "date": [],
            "other": [],
            "custom": []
        }

        for field in fields:
            field_id = field.get("technical_id") or field.get("id", "")
            category = self.classify_field(field_id)
            classified[category].append(field)

        for category in classified:
            classified[category].sort(
                key=lambda x: (x.get("technical_id") or x.get("id", "")).lower()
            )

        return (classified["identifier"] +
                classified["date"] +
                classified["other"] +
                classified["custom"])

    def _is_internal_field(self, field_id: str, attributes: Dict) -> bool:
        """Determina si un campo es técnico interno."""
        # Campos que solo son para sistema
        internal_indicators = [
            "attachment","calculated", "sys"  
        ]

        field_id_lower = field_id.lower()
        for indicator in internal_indicators:
            if indicator in field_id_lower:
                return True

        field_type = attributes.get("type", "").lower()
        if field_type in ["attachment", "calculated"]:
            return True
        return False