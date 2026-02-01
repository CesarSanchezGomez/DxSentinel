from pydantic import BaseModel, Field, validator
from typing import Optional, List
import re


class ProcessRequest(BaseModel):
    """Modelo para solicitud de procesamiento de archivos XML"""
    
    # CAMPOS OBLIGATORIOS para metadata - mantener 'id' como espera orchestrator
    id: str = Field(
        ...,
        description="ID único del proceso para metadata. Ej: '1769928382_USA'"
    )
    cliente: str = Field(
        ...,
        description="Nombre del cliente. Obligatorio para metadata"
    )
    consultor: str = Field(
        ...,
        description="Nombre del consultor. Obligatorio para metadata"
    )
    
    # Campos existentes
    main_file_id: str = Field(
        ...,
        description="ID del archivo XML principal"
    )
    csf_file_id: Optional[str] = Field(
        None,
        description="ID del archivo CSF (opcional)"
    )
    language_code: str = Field(
        "en-us",
        description="Código de idioma para el template (en-us, es-mx)"
    )
    country_codes: Optional[List[str]] = Field(
        None,
        description="Lista de códigos de país a procesar"
    )
    
    # Campo alias para compatibilidad
    countries: Optional[List[str]] = Field(
        None,
        alias="countries",
        description="Alias para country_codes (compatibilidad)"
    )

    @validator('id')
    def validate_id(cls, v):
        """Valida que el id sea válido para nombres de directorio"""
        if not v:
            raise ValueError("id no puede estar vacío")
        if re.search(r'[<>:"/\\|?*]', v):
            raise ValueError("id contiene caracteres inválidos para nombre de directorio")
        if len(v) > 100:
            raise ValueError("id demasiado largo (máx 100 caracteres)")
        return v

    @validator('cliente')
    def validate_cliente(cls, v):
        if not v or not v.strip():
            raise ValueError("cliente no puede estar vacío")
        return v.strip()

    @validator('consultor')
    def validate_consultor(cls, v):
        if not v or not v.strip():
            raise ValueError("consultor no puede estar vacío")
        return v.strip()

    @validator('language_code')
    def validate_language_code(cls, v):
        valid_codes = ['en-us', 'es-mx']
        if v not in valid_codes:
            raise ValueError(f"language_code debe ser uno de: {valid_codes}")
        return v

    @validator('country_codes', 'countries')
    def validate_country_codes(cls, v, values, **kwargs):
        """Valida que los códigos de país sean válidos si se proporcionan"""
        if v is None:
            return v
        
        for country in v:
            if not re.match(r'^[A-Z]{2,3}$', country):
                raise ValueError(f"Código de país inválido: {country}")
        
        return v

    def get_countries(self) -> List[str]:
        """Obtiene la lista de países a procesar"""
        if self.country_codes:
            return self.country_codes
        elif self.countries:
            return self.countries
        elif self.csf_file_id:
            # Si hay CSF pero no países, retornar lista vacía
            # El endpoint validará esto
            return []
        else:
            # Sin CSF, no se necesitan países
            return []


class ProcessResponse(BaseModel):
    """Modelo para respuesta de procesamiento"""
    
    success: bool
    message: str
    output_file: Optional[str] = None
    metadata_file: Optional[str] = None
    field_count: int = 0
    processing_time: float = 0.0
    countries_processed: Optional[List[str]] = None