# transformer/column_parser.py
"""
Parser de identificadores de columna compuestos.
"""

import re
from typing import Optional, Tuple, List
from .models import ParsedColumn, TransformationError
from .errors import TransformerErrors


class ColumnParser:
    """Parsea identificadores de columna Golden Record."""
    
    # Patrones para identificar estructuras
    # Formato básico: element_field
    # Formato CSF: [country]_[element]_[field] o element_field con is_country_specific
    
    @staticmethod
    def parse_column(column_name: str) -> Tuple[Optional[ParsedColumn], Optional[TransformationError]]:
        """
        Parsea un identificador de columna Golden Record.
        
        NUEVA ESTRATEGIA: Reconocer patrones CSF específicos del XMLParser.
        """
        if not column_name or not isinstance(column_name, str):
            return None, TransformerErrors.invalid_column_composition(
                str(column_name), "Nombre de columna vacío o no string"
            )
        
        column_name = column_name.strip()
        
        # Validar formato básico: debe contener al menos un _
        if '_' not in column_name:
            return None, TransformerErrors.invalid_column_composition(
                column_name, "Formato inválido: debe contener '_'"
            )
        
        # **NUEVO: Lista de elementos duplicados conocidos por XMLParser**
        DUPLICATED_ELEMENTS = {
            'workPermitInfo_RFC', 'workPermitInfo_IMMS',
            'homeAddress_home', 'homeAddress_fiscal'
        }
        
        # **NUEVO: Elementos compuestos (con _ en el nombre)**
        COMPOUND_ELEMENTS = {
            'homeAddress_home', 'homeAddress_fiscal',
            'workPermitInfo_RFC', 'workPermitInfo_IMMS',
            'globalInfo', 'biographicalInfoLoc'
        }
        
        # Separar por _
        parts = column_name.split('_')
        
        # **NUEVO ESTRATEGIA PARA CSF:**
        # Patrón: COUNTRY_ELEMENT_FIELD o COUNTRY_ELEMENTCOMPOUND_FIELD
        # Ejemplos:
        # 1. MEX_homeAddress_fiscal_street → MEX, homeAddress_fiscal, street
        # 2. MEX_jobInfo_position → MEX, jobInfo, position
        # 3. personInfo_country-of-birth → personInfo, country-of-birth (no CSF)
        
        is_country_specific = False
        country_code = None
        element_id = None
        field_id = None
        
        # Verificar si la primera parte es código de país
        if len(parts) >= 3 and ColumnParser._looks_like_country_code(parts[0]):
            country_code = parts[0]
            is_country_specific = True
            
            # **CASO 1: Elemento compuesto (homeAddress_fiscal, workPermitInfo_RFC)**
            # Verificar si parts[1] + "_" + parts[2] es un elemento compuesto conocido
            if len(parts) >= 4:
                potential_compound = f"{parts[1]}_{parts[2]}"
                if potential_compound in COMPOUND_ELEMENTS:
                    # Es elemento compuesto: MEX_homeAddress_fiscal_street
                    element_id = potential_compound  # homeAddress_fiscal
                    field_id = '_'.join(parts[3:])   # street
                else:
                    # Es elemento simple: MEX_jobInfo_position
                    element_id = parts[1]            # jobInfo
                    field_id = '_'.join(parts[2:])   # position
            elif len(parts) == 3:
                # MEX_element_field (sin elemento compuesto)
                element_id = parts[1]                # element
                field_id = parts[2]                  # field
            else:
                # Formato inválido
                return None, TransformerErrors.invalid_column_composition(
                    column_name, f"Formato CSF inválido: {len(parts)} partes"
                )
        
        else:
            # **CASO NO CSF: elemento_field**
            is_country_specific = False
            country_code = None
            
            if len(parts) >= 2:
                # **VERIFICAR: ¿Es un elemento compuesto?**
                # Ejemplo: homeAddress_fiscal_street → homeAddress_fiscal, street
                potential_compound = f"{parts[0]}_{parts[1]}"
                
                if potential_compound in COMPOUND_ELEMENTS and len(parts) >= 3:
                    # Es elemento compuesto sin país
                    element_id = potential_compound
                    field_id = '_'.join(parts[2:])
                else:
                    # Es elemento simple
                    element_id = parts[0]
                    field_id = '_'.join(parts[1:])
            else:
                return None, TransformerErrors.invalid_column_composition(
                    column_name, f"Partes insuficientes: {len(parts)}"
                )
        
        # Validar que no sean vacíos
        if not element_id:
            return None, TransformerErrors.invalid_column_composition(
                column_name, "Elemento vacío"
            )
        
        if not field_id:
            return None, TransformerErrors.invalid_column_composition(
                column_name, "Campo vacío"
            )
        
        # **IMPORTANTE: Para campos CSF, el element_id debe ser SIN prefijo país**
        # Ej: MEX_homeAddress_fiscal → element_id="homeAddress_fiscal"
        
        # Crear ParsedColumn
        parsed_column = ParsedColumn(
            original_name=column_name,
            element_id=element_id,  # **SIN prefijo país incluso para CSF**
            field_id=field_id,
            is_country_specific=is_country_specific,
            country_code=country_code
        )
        
        return parsed_column, None
    
    @staticmethod
    def _looks_like_country_code(code: str) -> bool:
        """
        Determina si un código parece ser de país.
        
        Args:
            code: Candidato a código de país
            
        Returns:
            True si parece ser código de país
        """
        if not code:
            return False
        
        # Longitud típica de códigos de país: 2-3 caracteres
        if not (2 <= len(code) <= 3):
            return False
        
        # Normalmente son mayúsculas
        if not code.isupper():
            return False
        
        # Solo letras (sin números ni caracteres especiales)
        if not code.isalpha():
            return False
        
        # Lista de códigos de país comunes (puede extenderse)
        common_countries = {
            'MEX', 'USA', 'CAN', 'BRA', 'ARG', 'CHL', 'COL', 'PER', 'ESP', 'FRA',
            'DEU', 'GBR', 'ITA', 'JPN', 'CHN', 'IND', 'AUS', 'NZL'
        }
        
        # Si está en la lista común, es muy probable
        if code in common_countries:
            return True
        
        # Si no está en la lista, aún podría ser válido
        # Devolver True para cualquier código de 2-3 letras mayúsculas
        return True

    @staticmethod
    def parse_all_columns(column_names: List[str]) -> Tuple[List[ParsedColumn], List[TransformationError]]:
        """
        Parsea todas las columnas de un CSV.
        
        Args:
            column_names: Lista de nombres de columna
            
        Returns:
            Tupla (lista de columnas parseadas, lista de errores)
        """
        parsed_columns = []
        errors = []
        
        for col_index, column_name in enumerate(column_names):
            parsed_column, error = ColumnParser.parse_column(column_name)
            
            if error:
                errors.append(error)
                # Crear un placeholder para mantener integridad
                parsed_columns.append(ParsedColumn(
                    original_name=column_name,
                    element_id=f"ERROR_{col_index}",
                    field_id=column_name,
                    is_country_specific=False
                ))
            elif parsed_column:
                parsed_columns.append(parsed_column)
            else:
                # Caso raro: parsed_column es None pero error también es None
                errors.append(TransformerErrors.invalid_column_composition(
                    column_name, "Parseo retornó None sin error"
                ))
                parsed_columns.append(ParsedColumn(
                    original_name=column_name,
                    element_id=f"UNKNOWN_{col_index}",
                    field_id=column_name,
                    is_country_specific=False
                ))
        
        return parsed_columns, errors