from typing import Dict, List


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
    def find_all_elements(node: Dict) -> List[Dict]:
        """
        Finds all hris-elements recursively.

        Args:
            node: Model node

        Returns:
            List of hris-element nodes
        """
        elements = []

        if node.get("tag") == "hris-element":
            elements.append(node)

        for child in node.get("children", []):
            elements.extend(GoldenRecordFieldFinder.find_all_elements(child))

        return elements
