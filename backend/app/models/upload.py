from pydantic import BaseModel, Field
from typing import Optional

class UploadResponse(BaseModel):
    success: bool
    message: str
    file_id: Optional[str] = None
    filename: Optional[str] = None