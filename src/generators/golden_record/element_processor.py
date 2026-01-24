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
        """
        try:
            structure = parsed_model.get("structure", {})
            
            # DEBUG: Mostrar estructura inicial
            print("\n🔍 ANALIZANDO ESTRUCTURA DEL MODELO:")
            self._debug_print_structure(structure, max_depth=4)
            
            # Encontrar elementos SDM (globales)
            sdm_elements = GoldenRecordFieldFinder.find_all_elements(structure, origin_filter="sdm")
            all_elements = GoldenRecordFieldFinder.find_all_elements(structure)
            non_csf_elements = [elem for elem in all_elements 
                              if GoldenRecordFieldFinder.get_element_origin(elem) != "csf"]
            
            # Combinar elementos SDM explícitos y no-CSF
            global_elements_dict = {}
            for elem in sdm_elements + non_csf_elements:
                elem_id = elem.get("technical_id") or elem.get("id", "")
                if elem_id and elem_id not in global_elements_dict:
                    origin = GoldenRecordFieldFinder.get_element_origin(elem) or "sdm"
                    global_elements_dict[elem_id] = {
                        "node": elem,
                        "origin": origin
                    }
                    print(f"📌 Elemento SDM encontrado: {elem_id} [origin={origin}]")
            
            # Encontrar todos los nodos país
            country_nodes = self._find_country_nodes(structure)
            print(f"\n🌍 NODOS PAÍS ENCONTRADOS: {len(country_nodes)}")
            
            # Procesar elementos CSF específicos por país
            country_specific_elements = {}
            for country_node in country_nodes:
                country_code = self._get_country_code(country_node)
                if not country_code:
                    continue
                
                print(f"\n📁 Procesando país: {country_code}")
                
                # Aplicar filtro por país si está configurado
                if self.target_country:
                    normalized_country_code = self._normalize_country_code(country_code)
                    if normalized_country_code != self._normalized_target_country:
                        print(f"  ⏩ Saltando país: {country_code}")
                        continue
                
                # Encontrar elementos CSF dentro de este país
                csf_elements_in_country = GoldenRecordFieldFinder.find_all_elements(country_node, origin_filter="csf")
                print(f"  🔧 Elementos CSF en {country_code}: {len(csf_elements_in_country)}")
                
                for elem in csf_elements_in_country:
                    elem_id = elem.get("technical_id") or elem.get("id", "")
                    if elem_id:
                        # IMPORTANTE: El element_id debe incluir el país
                        # Si elem_id es "homeAddress_csf", queremos "MEX_homeAddress"
                        clean_elem_id = elem_id.replace("_csf", "")
                        
                        # Agregar prefijo de país
                        country_element_id = f"{country_code}_{clean_elem_id}"
                        
                        # DEBUG: Mostrar información detallada
                        attributes = elem.get("attributes", {}).get("raw", {})
                        data_country = attributes.get("data-country", "")
                        print(f"    • Elemento CSF: {elem_id}")
                        print(f"      → clean_elem_id: {clean_elem_id}")
                        print(f"      → country_element_id: {country_element_id}")
                        print(f"      → data-country: {data_country}")
                        
                        country_specific_elements[country_element_id] = {
                            "node": elem,
                            "country_code": country_code,
                            "origin": "csf",
                            "original_element_id": elem_id,
                            "clean_element_id": clean_elem_id
                        }
            
            # Procesar elementos SDM globales
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
                        print(f"✅ Elemento SDM procesado: {elem_id} ({len(element_data['fields'])} campos)")
                    del global_elements_dict[elem_id]
            
            # Procesar elementos CSF específicos por país
            csf_elements_list = []
            for element_id, elem_info in country_specific_elements.items():
                country_code = elem_info["country_code"]
                
                print(f"\n🔄 Procesando elemento CSF: {element_id}")
                print(f"   • País: {country_code}")
                print(f"   • Origin: {elem_info['origin']}")
                print(f"   • Original ID: {elem_info['original_element_id']}")
                
                element_data = self._process_element(
                    elem_info["node"], 
                    element_id,  # Esto ya es "MEX_homeAddress"
                    origin="csf",
                    is_country_specific=True,
                    country_code=country_code
                )
                if element_data["fields"]:
                    csf_elements_list.append(element_data)
                    print(f"   ✅ {len(element_data['fields'])} campos procesados")
                    
                    # DEBUG: Mostrar algunos campos
                    for i, field in enumerate(element_data["fields"][:3]):
                        print(f"      • {field['full_field_id']}")
                    if len(element_data["fields"]) > 3:
                        print(f"      ... y {len(element_data['fields']) - 3} más")
            
            # Combinar resultados
            all_elements_list = processed + custom_elements + csf_elements_list
            
            result = {
                "elements": all_elements_list,
                "country_count": len(country_nodes),
                "csf_elements_count": len(csf_elements_list),
                "sdm_elements_count": len(processed + custom_elements),
                "target_country": self.target_country,
                "include_all_countries": self.target_country is None
            }
            
            print(f"\n📊 RESUMEN FINAL:")
            print(f"   • Elementos SDM globales: {len(processed + custom_elements)}")
            print(f"   • Elementos CSF específicos: {len(csf_elements_list)}")
            print(f"   • Total elementos: {len(all_elements_list)}")
            
            return result

        except Exception as e:
            raise ElementNotFoundError(f"Error processing model: {str(e)}") from e
        
    def _debug_print_structure(self, node: Dict, level: int = 0, max_depth: int = 3):
        """Función de debug para imprimir estructura."""
        if level > max_depth:
            return
        
        indent = "  " * level
        tag = node.get("tag", "")
        elem_id = node.get("technical_id") or node.get("id", "")
        attributes = node.get("attributes", {}).get("raw", {})
        data_origin = attributes.get("data-origin", "")
        data_country = attributes.get("data-country", "")
        
        if tag in ["XMLDocument", "country", "hris-element", "hris-field"] or data_origin:
            origin_info = f" [origin={data_origin}]" if data_origin else ""
            country_info = f" [country={data_country}]" if data_country else ""
            print(f"{indent}{tag}: {elem_id}{origin_info}{country_info}")
        
        for child in node.get("children", []):
            self._debug_print_structure(child, level + 1, max_depth)

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
                        origin: str = "",
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

            # Construir full_field_id según el origen
            if origin == "csf" and is_country_specific and country_code:
                # IMPORTANTE: Para campos CSF, necesitamos construir el ID completo:
                # Formato: [país]_[elemento]_[campo]
                
                # 1. Asegurar que element_id tenga el prefijo de país
                if not element_id.startswith(f"{country_code}_"):
                    element_id_with_country = f"{country_code}_{element_id}"
                else:
                    element_id_with_country = element_id
                
                # 2. field_id es solo el nombre base del campo (ej: "payScaleArea")
                # Construir full_field_id completo
                full_field_id = f"{element_id_with_country}_{field_id}"
                
                # 3. NOTA: No usar data-full-id o field_id completo porque
                # los field_id en XML son solo los nombres base
                
            else:
                # Para campos SDM: [elemento]_[campo]
                full_field_id = f"{element_id}_{field_id}"

            if include and full_field_id not in self.global_field_ids:
                self.global_field_ids.add(full_field_id)
                element_fields.append({
                    "field_id": field_id,
                    "full_field_id": full_field_id,
                    "node": field_node,
                    "origin": origin,
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
            "origin": origin,
            "fields": ordered_fields,
            "is_country_specific": is_country_specific,
            "country_code": country_code,
            "field_count": len(ordered_fields)
        }