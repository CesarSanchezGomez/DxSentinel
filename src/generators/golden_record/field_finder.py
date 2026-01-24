from typing import Dict, List, Optional


class GoldenRecordFieldFinder:
    """Finds hris-field recursively in the tree."""

    @staticmethod
    def find_all_fields(node: Dict, include_nested: bool = True) -> List[Dict]:
        """
        Finds all hris-field nodes recursively.

        Args:
            node: Model node
            include_nested: If True, searches entire hierarchy

        Returns:
            List of hris-field nodes
        """
        fields = []

        if node.get("tag") == "hris-field":
            fields.append(node)

        if include_nested:
            for child in node.get("children", []):
                fields.extend(GoldenRecordFieldFinder.find_all_fields(child, include_nested))
        else:
            for child in node.get("children", []):
                if child.get("tag") == "hris-field":
                    fields.append(child)

        return fields

    @staticmethod
    def find_all_elements(node: Dict, origin_filter: Optional[str] = None) -> List[Dict]:
        """
        Finds all hris-elements recursively, optionally filtered by data-origin.

        Args:
            node: Model node
            origin_filter: Filter by data-origin attribute (e.g., "sdm", "csf")

        Returns:
            List of hris-element nodes
        """
        elements = []

        if node.get("tag") == "hris-element":
            # Check origin filter if specified
            if origin_filter:
                attributes = node.get("attributes", {}).get("raw", {})
                element_origin = attributes.get("data-origin", "")
                if element_origin == origin_filter:
                    elements.append(node)
            else:
                elements.append(node)

        for child in node.get("children", []):
            elements.extend(GoldenRecordFieldFinder.find_all_elements(child, origin_filter))

        return elements

    @staticmethod
    def get_element_origin(element_node: Dict) -> str:
        """
        Gets the data-origin of an element.
        
        Args:
            element_node: hris-element node
            
        Returns:
            Origin string (e.g., "sdm", "csf", or empty string)
        """
        attributes = element_node.get("attributes", {}).get("raw", {})
        return attributes.get("data-origin", "")