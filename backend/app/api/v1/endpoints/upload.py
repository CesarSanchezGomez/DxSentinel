from fastapi import APIRouter, UploadFile, File, HTTPException
from ....models.upload import UploadResponse
from ....services.file_service import FileService
from ....core.config import settings

router = APIRouter()


@router.post("/", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Only XML files are allowed")

    content = await file.read()

    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        file_id, file_path = FileService.save_uploaded_file(content, file.filename)

        return UploadResponse(
            success=True,
            message="File uploaded successfully",
            file_id=file_id,
            filename=file.filename
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")