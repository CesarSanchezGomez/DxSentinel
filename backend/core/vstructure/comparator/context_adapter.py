# comparator/context_adapter.py
"""
Adaptador entre metadata XML y contexto de validación.
Lee metadata desde el PICKLE (document.pkl) que contiene XMLDocument.
"""

import pickle
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import sys

# Intentar importar los tipos de parsing si están disponibles
try:
    from parsing import load_from_metadata
    PARSING_AVAILABLE = True
except ImportError:
    PARSING_AVAILABLE = False

from .models import MetadataContext, EntityMetadata, FieldMetadata
from .errors import ComparatorErrors


class MetadataAdapter:
    """Adapta metadata XMLDocument al formato necesario para validación."""
    
    @classmethod
    def load_and_adapt_metadata(
        cls, 
        instance_id: str, 
        version: Optional[str] = None
    ) -> MetadataContext:
        """
        Carga metadata desde el sistema de archivos y la adapta.
        
        Args:
            instance_id: ID de instancia metadata (ej: "NADRO")
            version: Versión específica (ej: "290126_v1")
            
        Returns:
            MetadataContext adaptado
        """
        try:
            print(f"🔍 Cargando metadata desde pickle...")
            
            # 1. Intentar usar load_from_metadata si está disponible (método preferido)
            if PARSING_AVAILABLE:
                print(f"   Usando módulo parsing para carga normalizada")
                result = load_from_metadata(
                    instance_id=instance_id,
                    version=version,
                    normalize=True
                )
                
                if 'error' in result:
                    raise ValueError(f"Error en parsing: {result['error']}")
                
                normalized = result.get('normalized', {})
                metadata_info = normalized.get('metadata', {})
                structure = normalized.get('structure', {})
                
                # Adaptar metadata parseada
                metadata_context = MetadataContext(
                    source_instance=metadata_info.get('instance_id', instance_id),
                    source_version=metadata_info.get('version', version or 'unknown'),
                    stats=normalized.get('statistics', {})
                )
                
                cls._extract_from_normalized_structure(structure, metadata_context)
                return metadata_context
            
            # 2. Fallback: cargar directamente del pickle
            print(f"   Cargando directamente desde pickle...")
            metadata_context = cls._load_from_pickle_direct(instance_id, version)
            return metadata_context
            
        except Exception as e:
            print(f"❌ Error cargando metadata: {e}")
            
            # Crear contexto de error
            error_context = MetadataContext(
                source_instance=instance_id,
                source_version=version or "error",
                stats={"error": str(e)}
            )
            error_context.field_by_full_path = {}
            return error_context
    
    @classmethod
    def _load_from_pickle_direct(
        cls, 
        instance_id: str, 
        version: Optional[str] = None
    ) -> MetadataContext:
        """
        Carga metadata directamente desde archivo pickle.
        ACTUALIZADO: Usa nueva estructura backend/storage/metadata/
        """
        # Buscar en la NUEVA estructura de metadata
        metadata_base = Path("backend/storage/metadata")
        
        if not metadata_base.exists():
            # Intentar estructuras alternativas
            metadata_base = Path("storage/metadata")
            if not metadata_base.exists():
                metadata_base = Path("metadata")
        
        if not metadata_base.exists():
            raise FileNotFoundError(f"Directorio metadata no encontrado: {metadata_base}")
        
        print(f"   Buscando en: {metadata_base}")
        
        # Buscar instancia
        instance_path = metadata_base / instance_id
        if not instance_path.exists():
            raise FileNotFoundError(f"Instancia metadata no encontrada: {instance_id}")
        print(f"   ✓ Instancia encontrada: {instance_path}")
        
        # Buscar versión específica o última
        if version:
            version_path = instance_path / version
        else:
            # Encontrar última versión
            version_dirs = sorted([
                d for d in instance_path.iterdir() 
                if d.is_dir() and any(f"_v{i}" in d.name for i in range(1, 10))
            ], reverse=True)
            
            if not version_dirs:
                version_dirs = sorted([d for d in instance_path.iterdir() if d.is_dir()], reverse=True)
            
            if not version_dirs:
                raise FileNotFoundError(f"No hay versiones en instancia: {instance_id}")
            
            version_path = version_dirs[0]
            version = version_path.name
        
        print(f"   ✓ Versión encontrada: {version_path}")
        
        # Cargar metadata.json para información
        metadata_file = version_path / f"metadata_{instance_id}.json"
        metadata_info = {}
        if metadata_file.exists():
            print(f"   Cargando metadata info: {metadata_file.name}")
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_info = json.load(f)
        else:
            # Intentar cualquier archivo metadata_*.json
            metadata_files = list(version_path.glob("metadata_*.json"))
            if metadata_files:
                metadata_file = metadata_files[0]
                print(f"   Cargando metadata info alternativo: {metadata_file.name}")
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_info = json.load(f)
        
        # Cargar document.pkl (XMLDocument serializado)
        pickle_file = version_path / f"document_{instance_id}.pkl"
        if not pickle_file.exists():
            # Intentar cualquier document_*.pkl
            pickle_files = list(version_path.glob("document_*.pkl"))
            if pickle_files:
                pickle_file = pickle_files[0]
            else:
                raise FileNotFoundError(f"Archivo pickle no encontrado en: {version_path}")
        
        print(f"   Leyendo pickle: {pickle_file.name}")
        
        with open(pickle_file, 'rb') as f:
            xml_document = pickle.load(f)
        
        # Crear contexto de metadata
        metadata_context = MetadataContext(
            source_instance=metadata_info.get('instance_id', instance_id),
            source_version=metadata_info.get('version', version),
            stats=metadata_info.get('stats', {})
        )
        
        # Extraer metadata del XMLDocument
        cls._extract_from_xml_document(xml_document, metadata_context)
        
        print(f"   ✓ Metadata cargada: {len(metadata_context.entities)} entidades, "
              f"{len(metadata_context.field_by_full_path)} campos")
        
        return metadata_context
    @classmethod
    def _extract_from_xml_document(
        cls, 
        xml_document, 
        metadata_context: MetadataContext
    ):
        """
        Extrae metadata de un objeto XMLDocument.
        
        Args:
            xml_document: Objeto XMLDocument del módulo parsing
            metadata_context: Contexto a poblar
        """
        try:
            # Acceder al root del documento
            root = xml_document.root
            
            # Función recursiva para procesar nodos
            def process_node(node, parent_element=None):
                # Acceder a propiedades del nodo
                tag = node.tag
                technical_id = node.technical_id if node.technical_id else ""
                node_type = node.node_type
                attributes = node.attributes
                
                # IMPORTANTE: node_type es un Enum, necesitamos convertirlo
                node_type_str = node_type.value if hasattr(node_type, 'value') else str(node_type)
                
                # Procesar hris-element
                if "hris-element" in tag.lower():
                    element_id = technical_id or attributes.get('id', '')
                    
                    if not element_id and 'id' in attributes:
                        element_id = attributes['id']
                    
                    if element_id:
                        # Determinar si es país específico
                        data_country = attributes.get('data-country')
                        data_origin = attributes.get('data-origin', '')
                        
                        # **CAMBIOS:**
                        # 1. Incluir UNKNOWN como CSF (para campos CSF genéricos)
                        is_country_specific = data_origin == "csf"
                        country_code = data_country if data_country not in ["", "UNKNOWN", None] else None
                        
                        # 2. Si es CSF pero país es UNKNOWN, tratarlo como global (no country specific)
                        if is_country_specific and country_code is None:
                            is_country_specific = False
                        
                        # **IMPORTANTE: Mantener el element_id COMPLETO como está en metadata**
                        # Ejemplos: homeAddress_fiscal, workPermitInfo_RFC
                        # NO dividir en país y elemento base
                        
                        # Crear metadata de entidad
                        if element_id not in metadata_context.entities:
                            metadata_context.entities[element_id] = EntityMetadata(
                                entity_id=element_id,
                                is_country_specific=is_country_specific,
                                country_code=country_code
                            )
                        
                        parent_element = element_id
                
                # Procesar hris-field
                elif "hris-field" in tag.lower():
                    if not parent_element:
                        return parent_element
                    
                    field_id = technical_id or attributes.get('id', '')
                    if not field_id:
                        return parent_element
                    
                    # **CAMBIOS: Construir full_path considerando CSF y elementos compuestos**
                    if parent_element in metadata_context.entities:
                        entity_meta = metadata_context.entities[parent_element]
                        
                        # Extraer atributos de validación
                        required = attributes.get('required', 'false').lower() == 'true'
                        data_type = attributes.get('type')
                        max_length = cls._parse_max_length(attributes.get('max-length'))
                        
                        if entity_meta.is_country_specific and entity_meta.country_code:
                            # **CASO CSF CON PAÍS ESPECÍFICO:**
                            # Crear DOS versiones del campo para búsqueda flexible
                            
                            # 1. Versión INTERNA: element_field (sin prefijo país)
                            # Ej: homeAddress_fiscal_street
                            internal_full_path = f"{parent_element}_{field_id}"
                            
                            # 2. Versión CSV: COUNTRY_element_field (con prefijo país)
                            # Ej: MEX_homeAddress_fiscal_street
                            csv_full_path = f"{entity_meta.country_code}_{parent_element}_{field_id}"
                            
                            # Crear metadata interna (principal)
                            internal_field_metadata = FieldMetadata(
                                element_id=parent_element,
                                field_id=field_id,
                                full_path=internal_full_path,
                                is_required=required,
                                data_type=data_type,
                                max_length=max_length,
                                pattern=attributes.get('pattern'),
                                is_country_specific=True,
                                country_code=entity_meta.country_code,
                                metadata_node=node,
                                attributes=attributes
                            )
                            
                            # Crear metadata para CSV (copia con full_path diferente)
                            csv_field_metadata = FieldMetadata(
                                element_id=f"{entity_meta.country_code}_{parent_element}",
                                field_id=field_id,
                                full_path=csv_full_path,
                                is_required=required,
                                data_type=data_type,
                                max_length=max_length,
                                pattern=attributes.get('pattern'),
                                is_country_specific=True,
                                country_code=entity_meta.country_code,
                                metadata_node=node,
                                attributes=attributes
                            )
                            
                            # Añadir AMBAS versiones al contexto
                            metadata_context.field_by_full_path[internal_full_path] = internal_field_metadata
                            metadata_context.field_by_full_path[csv_full_path] = csv_field_metadata
                            
                            # **NUEVO: También crear entidad con prefijo para búsqueda directa**
                            country_element_id = f"{entity_meta.country_code}_{parent_element}"
                            if country_element_id not in metadata_context.entities:
                                metadata_context.entities[country_element_id] = EntityMetadata(
                                    entity_id=country_element_id,
                                    is_country_specific=True,
                                    country_code=entity_meta.country_code
                                )
                            
                            # Añadir campo a ambas entidades
                            original_entity = metadata_context.entities[parent_element]
                            original_entity.fields[field_id] = internal_field_metadata
                            
                            country_entity = metadata_context.entities[country_element_id]
                            country_entity.fields[field_id] = csv_field_metadata
                            
                            if required:
                                original_entity.required_fields.add(field_id)
                                country_entity.required_fields.add(field_id)
                            
                            return parent_element  # Continuar con mismo parent
                        
                        else:
                            # **CASO NO CSF O CSF SIN PAÍS (UNKNOWN):**
                            # Usar guión bajo para coincidir con CSV
                            full_path = f"{parent_element}_{field_id}"
                    else:
                        # **FALLBACK: Si no hay metadata de entidad**
                        full_path = f"{parent_element}_{field_id}"
                    
                    # **SOLO PARA CAMPOS NO CSF: extraer atributos y crear metadata normal**
                    # (Los campos CSF ya fueron procesados arriba)
                    if not (parent_element in metadata_context.entities and 
                           metadata_context.entities[parent_element].is_country_specific and
                           metadata_context.entities[parent_element].country_code):
                        
                        required = attributes.get('required', 'false').lower() == 'true'
                        data_type = attributes.get('type')
                        max_length = cls._parse_max_length(attributes.get('max-length'))
                        
                        field_metadata = FieldMetadata(
                            element_id=parent_element,
                            field_id=field_id,
                            full_path=full_path,
                            is_required=required,
                            data_type=data_type,
                            max_length=max_length,
                            pattern=attributes.get('pattern'),
                            is_country_specific=parent_element.startswith(("MEX_", "USA_", "BRA_", "NADRO_")),
                            country_code=parent_element.split("_")[0] if "_" in parent_element else None,
                            metadata_node=node,
                            attributes=attributes
                        )
                        
                        # Añadir al contexto
                        metadata_context.field_by_full_path[full_path] = field_metadata
                        
                        # Añadir a la entidad
                        if parent_element in metadata_context.entities:
                            entity_metadata = metadata_context.entities[parent_element]
                            entity_metadata.fields[field_id] = field_metadata
                            
                            if required:
                                entity_metadata.required_fields.add(field_id)
                    
                    return parent_element
                
                # **CAMBIOS: Procesar otros tipos de elementos que no son hris-element**
                # (como workPermitInfo_IMMS, workPermitInfo_RFC que pueden no tener tag hris-element)
                elif node_type_str == "element" and technical_id:
                    # Para elementos que pueden no tener el tag exacto pero son elementos
                    element_id = technical_id
                    
                    if element_id and element_id not in metadata_context.entities:
                        # Verificar si parece ser variante de elemento conocido
                        if element_id.startswith(("workPermitInfo_", "homeAddress_")):
                            metadata_context.entities[element_id] = EntityMetadata(
                                entity_id=element_id,
                                is_country_specific=False,
                                country_code=None
                            )
                    
                    parent_element = element_id
                
                # Procesar hijos recursivamente
                children = node.children if hasattr(node, 'children') else []
                for child in children:
                    parent_element = process_node(child, parent_element)
                
                return parent_element
            
            # Procesar desde la raíz
            process_node(root)
            
            print(f"   ✓ Extraídos {len(metadata_context.entities)} entidades, "
                  f"{len(metadata_context.field_by_full_path)} campos")
            
            # **NUEVO: Log adicional para debugging**
            csf_fields_with_prefix = sum(1 for path in metadata_context.field_by_full_path.keys() 
                                       if any(path.startswith(prefix) for prefix in ['MEX_', 'USA_', 'BRA_']))
            print(f"   📊 Campos CSF con prefijo país creados: {csf_fields_with_prefix}")
            
        except Exception as e:
            print(f"⚠ Error extrayendo de XMLDocument: {e}")
            import traceback
            traceback.print_exc()
            # Continuar con contexto vacío pero no fallar
    
    @classmethod
    def _extract_from_normalized_structure(
        cls,
        structure: Dict[str, Any],
        metadata_context: MetadataContext
    ):
        """
        Extrae metadata de estructura normalizada.
        """
        # Usar el método existente de extracción
        cls._extract_field_metadata(structure, metadata_context)
    
    @staticmethod
    def _extract_field_metadata(
        node: Dict[str, Any], 
        metadata_context: MetadataContext,
        current_path: str = "",
        parent_element: Optional[str] = None
    ) -> Optional[str]:
        """
        Extrae recursivamente metadata de campos de estructura normalizada.
        
        Returns:
            El parent_element actual (puede cambiar durante la recursión)
        """
        if not isinstance(node, dict):
            return parent_element
        
        node_tag = node.get("tag", "")
        technical_id = node.get("technical_id", "")
        attributes = node.get("attributes", {})
        node_type = node.get("node_type", "")
        
        # **CAMBIOS: Manejar attributes nested (raw/normalized)**
        raw_attributes = {}
        if isinstance(attributes, dict):
            if "raw" in attributes:
                raw_attributes = attributes.get("raw", {})
            else:
                raw_attributes = attributes
        
        current_path = f"{current_path}/{node_tag}"
        
        # Procesar hris-element
        if "hris-element" in node_tag.lower():
            element_id = technical_id or raw_attributes.get("id", "")
            
            if element_id:
                # Determinar si es país específico
                data_country = raw_attributes.get("data-country")
                data_origin = raw_attributes.get("data-origin", "")
                
                # **CAMBIOS:**
                # 1. Incluir UNKNOWN como CSF (para campos CSF genéricos)
                is_country_specific = data_origin == "csf"
                country_code = data_country if data_country not in ["", "UNKNOWN", None] else None
                
                # 2. Si es CSF pero país es UNKNOWN, tratarlo como global
                if is_country_specific and country_code is None:
                    is_country_specific = False
                
                # **IMPORTANTE: Mantener el element_id COMPLETO**
                # NO dividir en país y elemento base
                
                # Crear metadata de entidad
                if element_id not in metadata_context.entities:
                    metadata_context.entities[element_id] = EntityMetadata(
                        entity_id=element_id,
                        is_country_specific=is_country_specific,
                        country_code=country_code
                    )
                
                parent_element = element_id
        
        # Procesar hris-field
        elif "hris-field" in node_tag.lower():
            if not parent_element:
                return parent_element
            
            field_id = technical_id or raw_attributes.get("id", "")
            if not field_id:
                return parent_element
            
            # **CAMBIOS: Construir full_path considerando CSF y elementos compuestos**
            if parent_element in metadata_context.entities:
                entity_meta = metadata_context.entities[parent_element]
                
                # Extraer atributos de validación
                required = raw_attributes.get("required", "false").lower() == "true"
                data_type = raw_attributes.get("type")
                max_length = MetadataAdapter._parse_max_length(raw_attributes.get("max-length"))
                
                if entity_meta.is_country_specific and entity_meta.country_code:
                    # **CASO CSF CON PAÍS ESPECÍFICO:**
                    # Crear DOS versiones del campo
                    
                    # 1. Versión INTERNA: element_field (sin prefijo país)
                    internal_full_path = f"{parent_element}_{field_id}"
                    
                    # 2. Versión CSV: COUNTRY_element_field (con prefijo país)
                    csv_full_path = f"{entity_meta.country_code}_{parent_element}_{field_id}"
                    
                    # Metadata interna (principal)
                    internal_field_metadata = FieldMetadata(
                        element_id=parent_element,
                        field_id=field_id,
                        full_path=internal_full_path,
                        is_required=required,
                        data_type=data_type,
                        max_length=max_length,
                        pattern=raw_attributes.get("pattern"),
                        is_country_specific=True,
                        country_code=entity_meta.country_code,
                        metadata_node=node,
                        attributes=raw_attributes
                    )
                    
                    # Metadata para CSV
                    csv_field_metadata = FieldMetadata(
                        element_id=f"{entity_meta.country_code}_{parent_element}",
                        field_id=field_id,
                        full_path=csv_full_path,
                        is_required=required,
                        data_type=data_type,
                        max_length=max_length,
                        pattern=raw_attributes.get("pattern"),
                        is_country_specific=True,
                        country_code=entity_meta.country_code,
                        metadata_node=node,
                        attributes=raw_attributes
                    )
                    
                    # Añadir AMBAS versiones
                    metadata_context.field_by_full_path[internal_full_path] = internal_field_metadata
                    metadata_context.field_by_full_path[csv_full_path] = csv_field_metadata
                    
                    # **NUEVO: Crear entidad con prefijo para búsqueda directa**
                    country_element_id = f"{entity_meta.country_code}_{parent_element}"
                    if country_element_id not in metadata_context.entities:
                        metadata_context.entities[country_element_id] = EntityMetadata(
                            entity_id=country_element_id,
                            is_country_specific=True,
                            country_code=entity_meta.country_code
                        )
                    
                    # Añadir campo a ambas entidades
                    original_entity = metadata_context.entities[parent_element]
                    original_entity.fields[field_id] = internal_field_metadata
                    
                    country_entity = metadata_context.entities[country_element_id]
                    country_entity.fields[field_id] = csv_field_metadata
                    
                    if required:
                        original_entity.required_fields.add(field_id)
                        country_entity.required_fields.add(field_id)
                    
                    return parent_element  # Continuar con mismo parent
                
                else:
                    # **CASO NO CSF O CSF SIN PAÍS:**
                    full_path = f"{parent_element}_{field_id}"
            else:
                full_path = f"{parent_element}_{field_id}"
            
            # **SOLO PARA CAMPOS NO CSF: crear metadata normal**
            if not (parent_element in metadata_context.entities and 
                   metadata_context.entities[parent_element].is_country_specific and
                   metadata_context.entities[parent_element].country_code):
                
                required = raw_attributes.get("required", "false").lower() == "true"
                data_type = raw_attributes.get("type")
                max_length = MetadataAdapter._parse_max_length(raw_attributes.get("max-length"))
                
                field_metadata = FieldMetadata(
                    element_id=parent_element,
                    field_id=field_id,
                    full_path=full_path,
                    is_required=required,
                    data_type=data_type,
                    max_length=max_length,
                    pattern=raw_attributes.get("pattern"),
                    is_country_specific=parent_element.startswith(("MEX_", "USA_", "BRA_", "NADRO_")),
                    country_code=parent_element.split("_")[0] if "_" in parent_element else None,
                    metadata_node=node,
                    attributes=raw_attributes
                )
                
                # Añadir al contexto
                metadata_context.field_by_full_path[full_path] = field_metadata
                
                # Añadir a la entidad
                if parent_element in metadata_context.entities:
                    entity_metadata = metadata_context.entities[parent_element]
                    entity_metadata.fields[field_id] = field_metadata
                    
                    if required:
                        entity_metadata.required_fields.add(field_id)
            
            return parent_element
        
        # **CAMBIOS: Procesar otros tipos de elementos**
        elif node_type == "element" and technical_id:
            # Para elementos como workPermitInfo_IMMS
            element_id = technical_id
            
            if element_id and element_id not in metadata_context.entities:
                if element_id.startswith(("workPermitInfo_", "homeAddress_")):
                    metadata_context.entities[element_id] = EntityMetadata(
                        entity_id=element_id,
                        is_country_specific=False,
                        country_code=None
                    )
            
            parent_element = element_id
        
        # Procesar hijos recursivamente
        children = node.get("children", [])
        for child in children:
            parent_element = MetadataAdapter._extract_field_metadata(
                child, metadata_context, current_path, parent_element
            )
        
        return parent_element
    
    @staticmethod
    def _parse_max_length(max_length_str: Optional[str]) -> Optional[int]:
        """Parsea valor de max-length a entero."""
        if not max_length_str:
            return None
        
        try:
            return int(str(max_length_str).strip())
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def adapt_parsed_metadata(
        cls, 
        parsed_metadata: Dict[str, Any]
    ) -> MetadataContext:
        """
        Adapta metadata ya parseada (fallback para JSON).
        
        Args:
            parsed_metadata: Metadata ya parseada
            
        Returns:
            MetadataContext adaptado
        """
        try:
            structure = parsed_metadata.get('structure', {})
            metadata_info = parsed_metadata.get('metadata', {})
            
            metadata_context = MetadataContext(
                source_instance=metadata_info.get('instance_id', 'unknown'),
                source_version=metadata_info.get('version', 'unknown'),
                stats=parsed_metadata.get('statistics', {})
            )
            
            cls._extract_field_metadata(structure, metadata_context)
            return metadata_context
            
        except Exception as e:
            error_context = MetadataContext(
                source_instance="error",
                source_version="error",
                stats={"error": str(e)}
            )
            error_context.field_by_full_path = {}
            return error_context
    
    @classmethod
    def create_mock_metadata(cls) -> MetadataContext:
        """
        Crea metadata de prueba para testing.
        
        Returns:
            MetadataContext con datos de prueba
        """
        metadata_context = MetadataContext(
            source_instance="test_mock",
            source_version="1.0.0"
        )
        
        # Ejemplo: metadata para personInfo
        person_info_entity = EntityMetadata(entity_id="personInfo")
        
        # Campo requerido
        birth_date_metadata = FieldMetadata(
            element_id="personInfo",
            field_id="date-of-birth",
            full_path="personInfo.date-of-birth",
            is_required=True,
            data_type="date",
            max_length=None
        )
        
        # Campo con longitud máxima
        country_metadata = FieldMetadata(
            element_id="personInfo",
            field_id="country-of-birth",
            full_path="personInfo.country-of-birth",
            is_required=False,
            data_type="string",
            max_length=100
        )
        
        # Campos para employmentInfo
        employment_entity = EntityMetadata(entity_id="employmentInfo")
        
        start_date_metadata = FieldMetadata(
            element_id="employmentInfo",
            field_id="start-date",
            full_path="employmentInfo.start-date",
            is_required=True,
            data_type="date",
            max_length=None
        )
        
        # Añadir campos a entidades
        person_info_entity.fields = {
            "date-of-birth": birth_date_metadata,
            "country-of-birth": country_metadata
        }
        person_info_entity.required_fields = {"date-of-birth"}
        
        employment_entity.fields = {
            "start-date": start_date_metadata
        }
        employment_entity.required_fields = {"start-date"}
        
        # Añadir entidades al contexto
        metadata_context.entities = {
            "personInfo": person_info_entity,
            "employmentInfo": employment_entity
        }
        
        # Añadir a field_by_full_path
        for entity in metadata_context.entities.values():
            for field_metadata in entity.fields.values():
                metadata_context.field_by_full_path[field_metadata.full_path] = field_metadata
        
        return metadata_context