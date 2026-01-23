from typing import Dict, List, Set
from .field_filter import FieldFilter
from .field_finder import GoldenRecordFieldFinder
from .exceptions import ElementNotFoundError


class ElementProcessor:
    """Processes elements according to Golden Record hierarchy."""

    ELEMENT_HIERARCHY = [
        "personInfo", "personalInfo", "employmentInfo", "jobInfo",
        "homeAddress", "phoneInfo", "emailInfo", "nationalIdCard",
        "emergencyContactPrimary", "personRelationshipInfo",
        "compInfo", "payComponentRecurring", "payComponentNonRecurring",
        "workPermitInfo", "globalAssignmentInfo"
    ]

    def __init__(self):
        self.field_filter = FieldFilter()
        self.global_field_ids: Set[str] = set()

    def process_model(self, parsed_model: Dict) -> Dict:
        """
        Processes model and generates Golden Record structure.

        Args:
            parsed_model: Parsed SDM model

        Returns:
            Dict with processed structure
        """
        try:
            structure = parsed_model.get("structure", {})
            all_elements = GoldenRecordFieldFinder.find_all_elements(structure)

            relevant_elements = {}
            for elem in all_elements:
                elem_id = elem.get("technical_id") or elem.get("id", "")
                if elem_id:
                    relevant_elements[elem_id] = elem

            processed = []
            custom_elements = []

            for elem_id in self.ELEMENT_HIERARCHY:
                if elem_id in relevant_elements:
                    element_data = self._process_element(relevant_elements[elem_id], elem_id)
                    if element_data["fields"]:
                        processed.append(element_data)
                    del relevant_elements[elem_id]

            for elem_id, elem_node in relevant_elements.items():
                element_data = self._process_element(elem_node, elem_id)
                if element_data["fields"]:
                    custom_elements.append(element_data)

            custom_elements.sort(key=lambda x: x["element_id"])

            return {
                "elements": processed + custom_elements
            }

        except Exception as e:
            raise ElementNotFoundError(f"Error processing model: {str(e)}") from e

    def _process_element(self, element_node: Dict, element_id: str) -> Dict:
        """Processes individual element with recursive field search."""
        all_fields = GoldenRecordFieldFinder.find_all_fields(element_node, include_nested=True)

        element_fields = []
        for field_node in all_fields:
            include, _ = self.field_filter.filter_field(field_node)

            field_id = field_node.get("technical_id") or field_node.get("id", "")
            if not field_id:
                continue

            full_field_id = f"{element_id}_{field_id}"

            if include and full_field_id not in self.global_field_ids:
                self.global_field_ids.add(full_field_id)
                element_fields.append({
                    "field_id": field_id,
                    "full_field_id": full_field_id,
                    "node": field_node
                })

        sorted_fields = self.field_filter.sort_fields([f["node"] for f in element_fields])

        ordered_fields = []
        for field_node in sorted_fields:
            field_id = field_node.get("technical_id") or field_node.get("id", "")
            field_meta = next((f for f in element_fields if f["field_id"] == field_id), None)
            if field_meta:
                ordered_fields.append(field_meta)

        return {
            "element_id": element_id,
            "fields": ordered_fields
        }
