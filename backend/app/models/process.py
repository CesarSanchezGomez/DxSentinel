from pydantic import BaseModel, Field
from typing import Optional, List


class ProcessRequest(BaseModel):
    main_file_id: str
    csf_file_id: Optional[str] = None
    language_code: str = Field(default="en-US", pattern="^[a-z]{2}(-[A-Z]{2})?$")
    country_codes: Optional[List[str]] = Field(default=None)  # CAMBIO: ahora es lista

    # Mantener compatibilidad con código legacy
    country_code: Optional[str] = Field(default=None, max_length=3)

    def get_countries(self) -> Optional[List[str]]:
        """Retorna lista de países, dando prioridad a country_codes"""
        if self.country_codes:
            return self.country_codes
        elif self.country_code:
            return [self.country_code]
        return None


class ProcessResponse(BaseModel):
    success: bool
    message: str
    output_file: Optional[str] = None
    metadata_file: Optional[str] = None
    field_count: Optional[int] = None
    processing_time: Optional[float] = None
    countries_processed: Optional[List[str]] = None  # NUEVO: lista de países procesados