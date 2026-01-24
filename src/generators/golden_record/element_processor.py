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
        "workPermitInfo", "globalAssignmentInfo"
    ]

    def __init__(self, target_country: Optional[str] = None):
        """
        Args:
            target_country: Código de país específico a incluir (ej: "MEX").
                           Si es None, incluye todos los países.
        """
        self.field_filter = FieldFilter()
        self.global_field_ids: Set[str] = set()
        self.target_country = target_country.upper() if target_country else None
        self._normalized_target_country = self._normalize_country_code(target_country) if target_country else None

    def _normalize_country_code(self, country_code: str) -> str:
        """Normaliza el código de país para comparación."""
        return country_code.strip().upper()

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
            
            # Encontrar todos los nodos país
            country_nodes = self._find_country_nodes(structure)
            
            if self.target_country and country_nodes:
                print(f"🎯 Filtrando por país: {self.target_country}")
            
            relevant_elements = {}
            for elem in all_elements:
                elem_id = elem.get("technical_id") or elem.get("id", "")
                if elem_id:
                    relevant_elements[elem_id] = {
                        "node": elem,
                        "country_code": None,
                        "is_country_specific": False
                    }
            
            # Procesar elementos dentro de países (con filtro si target_country está definido)
            country_elements = {}
            for country_node in country_nodes:
                country_code = self._get_country_code(country_node)
                if not country_code:
                    continue
                
                # Aplicar filtro por país si está configurado
                if self.target_country:
                    normalized_country_code = self._normalize_country_code(country_code)
                    if normalized_country_code != self._normalized_target_country:
                        print(f"  ⏩ Saltando país: {country_code} (no coincide con {self.target_country})")
                        continue
                
                # Encontrar elementos dentro de este país
                country_elements_list = GoldenRecordFieldFinder.find_all_elements(country_node)
                for elem in country_elements_list:
                    elem_id = elem.get("technical_id") or elem.get("id", "")
                    if elem_id:
                        unique_id = f"{country_code}_{elem_id}"
                        country_elements[unique_id] = {
                            "node": elem,
                            "country_code": country_code,
                            "is_country_specific": True,
                            "original_element_id": elem_id
                        }
            
            processed = []
            custom_elements = []
            
            # Procesar elementos de la jerarquía principal (sin país) - SIEMPRE incluidos
            for elem_id in self.ELEMENT_HIERARCHY:
                if elem_id in relevant_elements:
                    element_data = self._process_element(
                        relevant_elements[elem_id]["node"], 
                        elem_id,
                        is_country_specific=False
                    )
                    if element_data["fields"]:
                        processed.append(element_data)
                    del relevant_elements[elem_id]
            
            # Procesar elementos personalizados principales (sin país) - SIEMPRE incluidos
            for elem_id, elem_info in relevant_elements.items():
                element_data = self._process_element(
                    elem_info["node"], 
                    elem_id,
                    is_country_specific=False
                )
                if element_data["fields"]:
                    custom_elements.append(element_data)
            
            # Procesar elementos específicos por país (solo si pasan el filtro)
            country_specific_elements = []
            for unique_id, elem_info in country_elements.items():
                country_code = elem_info["country_code"]
                original_elem_id = elem_info["original_element_id"]
                
                # Crear ID único que incluya el país
                country_element_id = f"{country_code}_{original_elem_id}"
                
                element_data = self._process_element(
                    elem_info["node"], 
                    country_element_id,
                    is_country_specific=True,
                    country_code=country_code
                )
                if element_data["fields"]:
                    country_specific_elements.append(element_data)
            
            # Ordenar todos los elementos
            custom_elements.sort(key=lambda x: x["element_id"])
            country_specific_elements.sort(key=lambda x: x["element_id"])
            
            result = {
                "elements": processed + custom_elements + country_specific_elements,
                "country_count": len(country_nodes),
                "country_specific_elements_count": len(country_specific_elements),
                "target_country": self.target_country,
                "include_all_countries": self.target_country is None
            }
            
            if self.target_country:
                print(f"✅ Filtrado completado. Elementos específicos de {self.target_country}: {len(country_specific_elements)}")
            else:
                print(f"🌍 Incluyendo todos los países. Elementos específicos: {len(country_specific_elements)}")
            
            return result

        except Exception as e:
            raise ElementNotFoundError(f"Error processing model: {str(e)}") from e

    def _find_country_nodes(self, node: Dict) -> List[Dict]:
        """
        Encuentra recursivamente todos los nodos país en el árbol.
        """
        countries = []
        
        if 'country' in node.get("tag", "").lower():
            countries.append(node)
        
        for child in node.get("children", []):
            countries.extend(self._find_country_nodes(child))
        
        return countries
    
    def _get_country_code(self, country_node: Dict) -> Optional[str]:
        """
        Extrae el código del país de un nodo país.
        """
        # Primero buscar en technical_id
        country_code = country_node.get("technical_id")
        if country_code:
            return country_code
        
        # Luego buscar en atributos
        attributes = country_node.get("attributes", {}).get("raw", {})
        country_code = attributes.get("id")
        if country_code:
            return country_code
        
        # Buscar en otros atributos comunes
        for attr_key in ["countryCode", "country-code", "code"]:
            country_code = attributes.get(attr_key)
            if country_code:
                return country_code
        
        # Finalmente buscar en labels si está disponible
        labels = country_node.get("labels", {})
        if labels and isinstance(labels, dict):
            for code, label in labels.items():
                if code and code != "default" and len(code) <= 3:  # Códigos de país son cortos
                    return code
        
        return None

    def _process_element(self, element_node: Dict, element_id: str, 
                        is_country_specific: bool = False, 
                        country_code: str = None) -> Dict:
        """
        Processes individual element with recursive field search.
        """
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
                    "node": field_node,
                    "is_country_specific": is_country_specific,
                    "country_code": country_code
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
            "fields": ordered_fields,
            "is_country_specific": is_country_specific,
            "country_code": country_code,
            "field_count": len(ordered_fields)
        }