from typing import Dict, List, Optional, Set
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
        "workPermitInfo", "workPermitInfo_CURP",
        "workPermitInfo_RFC", "globalAssignmentInfo", "jobRelationsInfo", "imInfo", "pensionPayoutsInfo", "globalInfo"
    ]

    def __init__(self, target_countries: Optional[List[str]] = None, target_country: Optional[str] = None):
        """
        Args:
            target_countries: List of country codes to include (e.g., ["MEX", "BRA"]).
            target_country: Single country code (legacy, converted to list).
                           If None, includes all countries.
        """
        if target_country and not target_countries:
            target_countries = [target_country]
        elif target_countries and isinstance(target_countries, str):
            target_countries = [target_countries]

        self.field_filter = FieldFilter()
        self.global_field_ids: Set[str] = set()
        self.target_countries = [c.upper() for c in target_countries] if target_countries else None

        print(f"[DEBUG] ElementProcessor initialized with target_countries={self.target_countries}")

    def _normalize_country_code(self, country_code: str) -> str:
        """Normalizes country code for comparison."""
        return country_code.strip().upper()

    def _should_include_country(self, country_code: str) -> bool:
        """
        Determina si un país debe ser incluido en el procesamiento.
        """
        if not self.target_countries:
            return True

        normalized = self._normalize_country_code(country_code)
        return normalized in self.target_countries

    def process_model(self, parsed_model: Dict) -> Dict:
        """
        Processes model and generates Golden Record structure.
        Supports processing multiple countries.
        """
        try:
            structure = parsed_model.get("structure", {})

            sdm_elements = GoldenRecordFieldFinder.find_all_elements(structure, origin_filter="sdm")
            all_elements = GoldenRecordFieldFinder.find_all_elements(structure)
            non_csf_elements = [elem for elem in all_elements
                                if GoldenRecordFieldFinder.get_element_origin(elem) != "csf"]

            global_elements_dict = {}
            for elem in sdm_elements + non_csf_elements:
                elem_id = elem.get("technical_id") or elem.get("id", "")
                if elem_id and elem_id not in global_elements_dict:
                    origin = GoldenRecordFieldFinder.get_element_origin(elem) or "sdm"
                    global_elements_dict[elem_id] = {
                        "node": elem,
                        "origin": origin
                    }

            country_nodes = self._find_country_nodes(structure)
            print(f"[DEBUG] Found {len(country_nodes)} country nodes total")

            filtered_country_nodes = []
            for country_node in country_nodes:
                country_code = self._get_country_code(country_node)
                if country_code and self._should_include_country(country_code):
                    filtered_country_nodes.append(country_node)
                    print(f"[DEBUG] Including country: {country_code}")
                elif country_code:
                    print(f"[DEBUG] Excluding country: {country_code}")

            print(f"[DEBUG] Processing {len(filtered_country_nodes)} countries")

            country_specific_elements = {}
            for country_node in filtered_country_nodes:
                country_code = self._get_country_code(country_node)
                if not country_code:
                    continue

                csf_elements_in_country = GoldenRecordFieldFinder.find_all_elements(country_node, origin_filter="csf")
                print(f"[DEBUG] Country {country_code}: {len(csf_elements_in_country)} CSF elements")

                for elem in csf_elements_in_country:
                    elem_id = elem.get("technical_id") or elem.get("id", "")
                    if elem_id:
                        clean_elem_id = elem_id.replace("_csf", "")
                        country_element_id = f"{country_code}_{clean_elem_id}"

                        country_specific_elements[country_element_id] = {
                            "node": elem,
                            "country_code": country_code,
                            "origin": "csf",
                            "original_element_id": elem_id,
                            "clean_element_id": clean_elem_id
                        }

            processed = []
            custom_elements = []

            for elem_id in self.ELEMENT_HIERARCHY:
                if elem_id in global_elements_dict:
                    elem_info = global_elements_dict[elem_id]
                    element_data = self._process_element(
                        elem_info["node"],
                        elem_id,
                        origin=elem_info["origin"],
                        is_country_specific=False
                    )
                    if element_data["fields"]:
                        processed.append(element_data)
                    del global_elements_dict[elem_id]

            csf_elements_list = []
            for element_id, elem_info in country_specific_elements.items():
                country_code = elem_info["country_code"]

                element_data = self._process_element(
                    elem_info["node"],
                    element_id,
                    origin="csf",
                    is_country_specific=True,
                    country_code=country_code
                )
                if element_data["fields"]:
                    csf_elements_list.append(element_data)

            all_elements_list = processed + custom_elements + csf_elements_list

            result = {
                "elements": all_elements_list,
                "country_count": len(filtered_country_nodes),
                "csf_elements_count": len(csf_elements_list),
                "sdm_elements_count": len(processed + custom_elements),
                "target_countries": self.target_countries,
                "include_all_countries": self.target_countries is None,
                "processed_countries": [self._get_country_code(node) for node in filtered_country_nodes]
            }

            print(f"[DEBUG] Final result: {len(all_elements_list)} total elements")
            print(f"[DEBUG] Countries processed: {result['processed_countries']}")

            return result

        except Exception as e:
            raise ElementNotFoundError(f"Error processing model: {str(e)}") from e

    def _find_country_nodes(self, node: Dict) -> List[Dict]:
        """Finds all country nodes in the tree."""
        countries = []

        if 'country' in node.get("tag", "").lower():
            countries.append(node)

        for child in node.get("children", []):
            countries.extend(self._find_country_nodes(child))

        return countries

    def _get_country_code(self, country_node: Dict) -> Optional[str]:
        """Extracts country code from a country node."""
        country_code = country_node.get("technical_id")
        if country_code:
            return country_code

        attributes = country_node.get("attributes", {}).get("raw", {})
        country_code = attributes.get("id")
        if country_code:
            return country_code

        for attr_key in ["countryCode", "country-code", "code"]:
            country_code = attributes.get(attr_key)
            if country_code:
                return country_code

        labels = country_node.get("labels", {})
        if labels and isinstance(labels, dict):
            for code, label in labels.items():
                if code and code != "default" and len(code) <= 3:
                    return code

        return None

    def _process_element(self, element_node: Dict, element_id: str,
                         origin: str = "",
                         is_country_specific: bool = False,
                         country_code: str = None) -> Dict:
        """Processes individual element with recursive field search."""
        all_fields = GoldenRecordFieldFinder.find_all_fields(element_node, include_nested=True)

        clean_element_id = element_id
        if is_country_specific and country_code and element_id.startswith(f"{country_code}_"):
            clean_element_id = element_id[len(country_code) + 1:]

        BUSINESS_KEYS_TO_INCLUDE = {
            'homeAddress': ['address-type']
        }

        element_fields = []
        for field_node in all_fields:
            field_id = field_node.get("technical_id") or field_node.get("id", "")
            if not field_id:
                continue

            is_business_key = False
            if clean_element_id in BUSINESS_KEYS_TO_INCLUDE:
                if field_id in BUSINESS_KEYS_TO_INCLUDE[clean_element_id]:
                    is_business_key = True

            if is_business_key:
                include = True
                exclusion_reason = None
            else:
                include, exclusion_reason = self.field_filter.filter_field(field_node)

            full_field_id = f"{clean_element_id}_{field_id}"

            if is_country_specific:
                if include:
                    element_fields.append({
                        "field_id": field_id,
                        "full_field_id": full_field_id,
                        "node": field_node,
                        "origin": origin,
                        "is_country_specific": is_country_specific,
                        "country_code": country_code,
                        "is_business_key": is_business_key
                    })
            else:
                if include and full_field_id not in self.global_field_ids:
                    self.global_field_ids.add(full_field_id)
                    element_fields.append({
                        "field_id": field_id,
                        "full_field_id": full_field_id,
                        "node": field_node,
                        "origin": origin,
                        "is_country_specific": is_country_specific,
                        "country_code": country_code,
                        "is_business_key": is_business_key
                    })

        sorted_fields = self.field_filter.sort_fields([f["node"] for f in element_fields])

        ordered_fields = []
        for field_node in sorted_fields:
            field_id = field_node.get("technical_id") or field_node.get("id", "")
            field_meta = next((f for f in element_fields if f["field_id"] == field_id), None)
            if field_meta:
                ordered_fields.append(field_meta)

        return {
            "element_id": clean_element_id,
            "origin": origin,
            "fields": ordered_fields,
            "is_country_specific": is_country_specific,
            "country_code": country_code,
            "field_count": len(ordered_fields)
        }


class GoldenRecordError(Exception):
    """Base exception for Golden Record generation errors."""
    pass


class ElementNotFoundError(GoldenRecordError):
    """Error when expected elements are not found."""
    pass


class FieldFilterError(GoldenRecordError):
    """Error in field filtering."""
    pass