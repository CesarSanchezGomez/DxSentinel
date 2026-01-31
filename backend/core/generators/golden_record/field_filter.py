from typing import Dict, List, Tuple, Optional, Set
import re
from .exceptions import FieldFilterError


class FieldFilter:
    """Filters and classifies fields according to Golden Record criteria."""

    IDENTIFIER_PATTERNS = [r"id$", r"number$", r"name$", r"code$"]
    DATE_PATTERNS = [r"date$", r"Date$", r"start", r"end", r"effective"]
    CUSTOM_PATTERNS = [r"custom", r"Custom", r"udf", r"UDF"]
    
    # Campos específicos a excluir por nombre base
    EXCLUDED_FIELD_IDS = {
        "companyEntryDate", "departmentEntryDate" , "jobEntryDate",
        "locationEntryDate", "positionEntryDate", "terminationDate",
        "timeInCompany", "timeInDepartment", "timeInJob", "end-date",
        "timeInLocation", "timeInPosition", "expiration-date", "employmentInfo_lastDateWorked",
        "okToRehire", "regretTermination", "compa-ratio", "range-penetration"
        }
    
    # Rangos de campos custom a excluir (sin necesidad de definirlos individualmente)
    # Formato: (base_name, start, end) donde start y end son inclusive
    EXCLUDED_CUSTOM_RANGES = [
        ("custom-string", 16, 20),   # Excluir custom-string16 al custom-string20
        ("custom-string", 81, 100)   # Excluir custom-string81 al custom-string100
    ]

    def __init__(self):
        self.identifier_patterns = [re.compile(p, re.IGNORECASE) for p in self.IDENTIFIER_PATTERNS]
        self.date_patterns = [re.compile(p, re.IGNORECASE) for p in self.DATE_PATTERNS]
        self.custom_patterns = [re.compile(p, re.IGNORECASE) for p in self.CUSTOM_PATTERNS]
        
        # Crear patrón regex para coincidencia exacta o parcial
        self.excluded_patterns = []
        for field_id in self.EXCLUDED_FIELD_IDS:
            pattern_str = r'^' + re.escape(field_id) + r'$'
            self.excluded_patterns.append(re.compile(pattern_str, re.IGNORECASE))
            
            if field_id.endswith('Id'):
                pattern_str = r'^' + re.escape(field_id[:-2]) + r'ID$'
                self.excluded_patterns.append(re.compile(pattern_str, re.IGNORECASE))
        
        # Generar campos custom excluidos dinámicamente a partir de los rangos
        self._generated_excluded_custom_fields = self._generate_custom_exclusions()

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
            
            # Obtener el ID base del campo (sin prefijos de país/elemento)
            field_id = field_node.get("technical_id") or field_node.get("id", "")
            
            # 1. Verificar visibilidad
            visibility = attributes.get("visibility", "").lower()
            if visibility == "none":
                return False, "visibility='none'"
            
            # 2. Verificar si es campo interno (existente)
            if self._is_internal_field(field_id, attributes):
                return False, "campo técnico interno"
            
            # 3. Verificar si el campo está en la lista de exclusión por nombre base
            if self._is_excluded_by_id(field_id):
                return False, "campo excluido por nombre"
            
            # 4. NUEVO: Verificar si es un campo custom en rango excluido
            if self._is_excluded_custom_field(field_id):
                return False, "campo custom en rango excluido"
            
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
        internal_indicators = [
            "attachment", "calculated", "sys"  
        ]

        field_id_lower = field_id.lower()
        for indicator in internal_indicators:
            if indicator in field_id_lower:
                return True

        field_type = attributes.get("type", "").lower()
        if field_type in ["attachment", "calculated"]:
            return True
        return False
    
    def _is_excluded_by_id(self, field_id: str) -> bool:
        """
        Verifica si un campo debe ser excluido por su nombre base.
        """
        if not field_id:
            return False
            
        field_id_lower = field_id.lower()
        
        # Verificar coincidencia exacta (case-insensitive)
        for excluded_id in self.EXCLUDED_FIELD_IDS:
            if field_id_lower == excluded_id.lower():
                return True
        
        # Verificar patrones regex para coincidencias más flexibles
        for pattern in self.excluded_patterns:
            if pattern.match(field_id):
                return True
        
        # Verificar si contiene algún patrón excluido como subcadena
        excluded_substrings = ["mdfSystem", "wf", "sync", "replication", "audit"]
        for substring in excluded_substrings:
            if substring.lower() in field_id_lower:
                if not self._is_valid_field_with_substring(field_id):
                    return True
        
        return False
    
    def _is_valid_field_with_substring(self, field_id: str) -> bool:
        """
        Determina si un campo que contiene subcadenas excluidas es válido.
        """
        field_id_lower = field_id.lower()
        
        valid_fields_with_excluded_patterns = {
            "systemUser", "systemAdministrator", "systemRole",
            "effectiveDate", "effectiveEndDate", "effectiveStartDate",
            "modifiedBy", "modifiedDate",
            "createdBy", "createdDate"
        }
        
        if field_id in valid_fields_with_excluded_patterns:
            return True
            
        valid_suffixes = ["date", "by", "name", "id", "code", "number"]
        for suffix in valid_suffixes:
            if field_id_lower.endswith(suffix):
                excluded_suffix_fields = ["lastmodifieddate", "createddate", 
                                         "lastmodifiedby", "createdby"]
                if field_id_lower not in excluded_suffix_fields:
                    return True
        
        return False
    
    def _generate_custom_exclusions(self) -> Set[str]:
        """
        Genera dinámicamente los nombres de campos custom a excluir basado en rangos.
        
        Returns:
            Conjunto con todos los nombres de campos custom en rangos excluidos
        """
        excluded_custom_fields = set()
        
        for base_name, start, end in self.EXCLUDED_CUSTOM_RANGES:
            for i in range(start, end + 1):
                field_name = f"{base_name}{i}"
                excluded_custom_fields.add(field_name)
                
                # También considerar variaciones comunes
                excluded_custom_fields.add(field_name.lower())
                excluded_custom_fields.add(field_name.upper())
        
        return excluded_custom_fields
    
    def _is_excluded_custom_field(self, field_id: str) -> bool:
        """
        Verifica si un campo es un custom field que está en un rango excluido.
        
        Args:
            field_id: ID del campo a verificar
            
        Returns:
            True si el campo está en un rango excluido de campos custom
        """
        if not field_id:
            return False
        
        field_id_lower = field_id.lower()
        
        # Verificar si es un campo custom en la lista generada
        if field_id_lower in self._generated_excluded_custom_fields:
            return True
        
        # Verificar dinámicamente si coincide con algún rango
        for base_name, start, end in self.EXCLUDED_CUSTOM_RANGES:
            base_name_lower = base_name.lower()
            
            # Verificar si el campo comienza con el nombre base
            if field_id_lower.startswith(base_name_lower):
                # Extraer la parte numérica
                suffix = field_id_lower[len(base_name_lower):]
                
                # Verificar si el sufijo es un número
                if suffix.isdigit():
                    number = int(suffix)
                    
                    # Verificar si el número está en el rango excluido
                    if start <= number <= end:
                        return True
        
        return False
    
    def add_excluded_field(self, field_id: str) -> None:
        """
        Añade un campo específico a la lista de exclusión.
        """
        if field_id and field_id not in self.EXCLUDED_FIELD_IDS:
            self.EXCLUDED_FIELD_IDS.add(field_id)
            pattern_str = r'^' + re.escape(field_id) + r'$'
            self.excluded_patterns.append(re.compile(pattern_str, re.IGNORECASE))
    
    def remove_excluded_field(self, field_id: str) -> bool:
        """
        Elimina un campo de la lista de exclusión.
        """
        if field_id in self.EXCLUDED_FIELD_IDS:
            self.EXCLUDED_FIELD_IDS.remove(field_id)
            self._rebuild_excluded_patterns()
            return True
        return False
    
    def _rebuild_excluded_patterns(self) -> None:
        """Reconstruye los patrones regex después de modificar la lista de exclusión."""
        self.excluded_patterns = []
        for field_id in self.EXCLUDED_FIELD_IDS:
            pattern_str = r'^' + re.escape(field_id) + r'$'
            self.excluded_patterns.append(re.compile(pattern_str, re.IGNORECASE))
            
            if field_id.endswith('Id'):
                pattern_str = r'^' + re.escape(field_id[:-2]) + r'ID$'
                self.excluded_patterns.append(re.compile(pattern_str, re.IGNORECASE))
    
    def get_excluded_fields(self) -> List[str]:
        """
        Retorna la lista actual de campos excluidos.
        """
        # Incluir campos de la lista estática
        excluded = sorted(self.EXCLUDED_FIELD_IDS)
        
        # Incluir campos custom generados dinámicamente
        custom_excluded = sorted(self._generated_excluded_custom_fields)
        
        return excluded + custom_excluded
    
    def clear_excluded_fields(self) -> None:
        """Limpia toda la lista de campos excluidos."""
        self.EXCLUDED_FIELD_IDS.clear()
        self.excluded_patterns = []
        self._generated_excluded_custom_fields.clear()
    
    def add_custom_exclusion_range(self, base_name: str, start: int, end: int) -> None:
        """
        Añade un nuevo rango de campos custom a excluir.
        
        Args:
            base_name: Nombre base del campo (ej: "custom-string")
            start: Número inicial del rango (inclusive)
            end: Número final del rango (inclusive)
        """
        if start > end:
            start, end = end, start
        
        # Verificar si el rango ya existe
        for i, (existing_base, existing_start, existing_end) in enumerate(self.EXCLUDED_CUSTOM_RANGES):
            if existing_base == base_name and existing_start <= start <= existing_end:
                # Ampliar rango existente si es necesario
                if end > existing_end:
                    self.EXCLUDED_CUSTOM_RANGES[i] = (base_name, existing_start, end)
                return
            elif existing_base == base_name and existing_start <= end <= existing_end:
                # Ampliar rango existente si es necesario
                if start < existing_start:
                    self.EXCLUDED_CUSTOM_RANGES[i] = (base_name, start, existing_end)
                return
        
        # Agregar nuevo rango
        self.EXCLUDED_CUSTOM_RANGES.append((base_name, start, end))
        
        # Regenerar campos excluidos
        self._generated_excluded_custom_fields = self._generate_custom_exclusions()
    
    def get_custom_exclusion_ranges(self) -> List[Tuple[str, int, int]]:
        """
        Retorna los rangos actuales de campos custom excluidos.
        
        Returns:
            Lista de tuplas (base_name, start, end)
        """
        return self.EXCLUDED_CUSTOM_RANGES.copy()