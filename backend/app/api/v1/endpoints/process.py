# backend/app/api/v1/endpoints/process.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from ....models.process import ProcessRequest, ProcessResponse
from ....services.parser_service import ParserService
from ....services.file_service import FileService
from ....core.config import get_settings
from ....auth.dependencies import get_current_user
from pathlib import Path
import logging

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/", response_model=ProcessResponse)
async def process_files(
        request: ProcessRequest,
        user=Depends(get_current_user)
):
    """Procesa archivos XML para generar CSV"""

    # Log para debugging
    logger.info(f"Processing request: {request}")
    logger.info(f"User: {user.email}")

    # Verificar archivo principal
    main_file_path = FileService.get_file_path(request.main_file_id)
    if not main_file_path:
        logger.error(f"Main file not found: {request.main_file_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Archivo principal no encontrado: {request.main_file_id}"
        )

    logger.info(f"Main file found: {main_file_path}")

    # Verificar archivo CSF (opcional)
    csf_file_path = None
    if request.csf_file_id:
        csf_file_path = FileService.get_file_path(request.csf_file_id)
        if not csf_file_path:
            logger.error(f"CSF file not found: {request.csf_file_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Archivo CSF no encontrado: {request.csf_file_id}"
            )
        logger.info(f"CSF file found: {csf_file_path}")

    try:
        logger.info(f"Starting parser service...")

        # Procesar archivos
        result = ParserService.process_files(
            main_file_path=str(main_file_path),
            csf_file_path=str(csf_file_path) if csf_file_path else None,
            language_code=request.language_code,
            country_code=request.country_code,
            output_dir=str(settings.OUTPUT_DIR)
        )

        logger.info(f"Processing completed: {result}")

        return ProcessResponse(
            success=True,
            message="Procesamiento completado exitosamente",
            output_file=Path(result["output_file"]).name,
            field_count=result["field_count"],
            processing_time=result["processing_time"]
        )

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Error de validación: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar archivos: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_file(
        filename: str,
        user=Depends(get_current_user)
):
    """Descarga archivo CSV generado"""

    # Validar nombre de archivo
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=400,
            detail="Nombre de archivo inválido"
        )

    file_path = settings.OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado"
        )

    # Verificar que el archivo esté dentro del directorio permitido
    if not file_path.resolve().is_relative_to(settings.OUTPUT_DIR.resolve()):
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado"
        )

    logger.info(f"User {user.email} downloading: {filename}")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='text/csv'
    )


@router.get("/list")
async def list_processed_files(user=Depends(get_current_user)):
    """Lista archivos CSV procesados"""
    try:
        output_files = list(settings.OUTPUT_DIR.glob("*.csv"))

        files = [
            {
                "filename": f.name,
                "size": f.stat().st_size,
                "created": f.stat().st_ctime,
                "download_url": f"/api/v1/process/download/{f.name}"
            }
            for f in output_files
        ]

        files.sort(key=lambda x: x["created"], reverse=True)

        return {
            "success": True,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al listar archivos: {str(e)}"
        )


@router.delete("/output/{filename}")
async def delete_output_file(
        filename: str,
        user=Depends(get_current_user)
):
    """Elimina un archivo CSV generado"""

    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")

    file_path = settings.OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    try:
        file_path.unlink()
        logger.info(f"User {user.email} deleted: {filename}")

        return {
            "success": True,
            "message": f"Archivo {filename} eliminado correctamente"
        }
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar archivo: {str(e)}"
        )