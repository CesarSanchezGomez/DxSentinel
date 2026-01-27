# backend/app/api/v1/endpoints/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from ....models.upload import UploadResponse
from ....services.file_service import FileService
from ....core.config import get_settings
from ....auth.dependencies import get_current_user

router = APIRouter()
settings = get_settings()


@router.post("/")  # CAMBIO: Solo "/" porque el prefix ya tiene /upload
async def upload_file(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    if not file.filename.lower().endswith(".xml"):
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten archivos XML"
        )

    content = await file.read()

    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Archivo demasiado grande. Máximo: {settings.MAX_UPLOAD_SIZE / (1024 * 1024):.0f}MB"
        )

    try:
        file_id, _ = FileService.save_uploaded_file(
            content=content,
            original_filename=file.filename
        )

        return UploadResponse(
            success=True,
            message="Archivo cargado exitosamente",
            file_id=file_id,
            filename=file.filename
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al cargar archivo: {str(e)}"
        )


@router.get("/list")  # CAMBIO: Solo "/list" -> /api/v1/upload/list
async def list_files(user=Depends(get_current_user)):
    try:
        files = FileService.list_files()
        return {
            "success": True,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al listar archivos: {str(e)}"
        )


@router.delete("/{file_id}")  # CAMBIO: Solo "/{file_id}" -> /api/v1/upload/{file_id}
async def delete_file(file_id: str, user=Depends(get_current_user)):
    if ".." in file_id or "/" in file_id or "\\" in file_id:
        raise HTTPException(
            status_code=400,
            detail="Nombre de archivo inválido"
        )

    deleted = FileService.delete_file(file_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado"
        )

    return {
        "success": True,
        "message": "Archivo eliminado correctamente"
    }