from pydantic import BaseModel, Field
from typing import Optional

class ProcessRequest(BaseModel):
    main_file_id: str
    csf_file_id: Optional[str] = None
    language_code: str = Field(default="en-US", pattern="^[a-z]{2}(-[A-Z]{2})?$")
    country_code: Optional[str] = Field(default=None, max_length=3)

class ProcessResponse(BaseModel):
    success: bool
    message: str
    output_file: Optional[str] = None
    field_count: Optional[int] = None
    processing_time: Optional[float] = None