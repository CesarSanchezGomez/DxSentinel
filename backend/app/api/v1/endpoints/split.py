from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from pathlib import Path
import tempfile
import zipfile
import shutil
import logging

from ....core.storage import StorageManager
from ....auth.dependencies import get_current_user
from backend.core.generators.splitter.layout_splitter import LayoutSplitter  # CORREGIR import

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/golden-record")
async def split_golden_record(
        golden_file: UploadFile = File(...),
        metadata_file: UploadFile = File(...),
        user=Depends(get_current_user)
):
    """Splits Golden Record into individual layouts and returns ZIP."""

    logger.info(f"Received split request from user {user.email}")
    logger.info(f"Golden file: {golden_file.filename}")
    logger.info(f"Metadata file: {metadata_file.filename}")

    if not golden_file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Golden Record must be CSV")

    if not metadata_file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Metadata must be JSON")

    try:
        # Leer archivos
        golden_content = await golden_file.read()
        metadata_content = await metadata_file.read()

        logger.info(f"Golden file size: {len(golden_content)} bytes")
        logger.info(f"Metadata file size: {len(metadata_content)} bytes")

        # Guardar temporalmente
        golden_path = StorageManager.save_upload(golden_content, f"golden_{user.email}.csv")
        metadata_path = StorageManager.save_upload(metadata_content, f"metadata_{user.email}.json")

        logger.info(f"Files saved: {golden_path}, {metadata_path}")

        # Procesar con LayoutSplitter
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Processing in temp dir: {temp_dir}")

            splitter = LayoutSplitter(str(metadata_path))
            layout_files = splitter.split_golden_record(str(golden_path), temp_dir)

            logger.info(f"Generated {len(layout_files)} layout files")

            if not layout_files:
                raise HTTPException(status_code=400, detail="No layouts were generated")

            # Crear ZIP
            zip_path = Path(temp_dir) / "layouts.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for layout_file in layout_files:
                    zipf.write(layout_file, Path(layout_file).name)
                    logger.info(f"Added to ZIP: {Path(layout_file).name}")

            # Copiar a outputs
            final_zip = StorageManager.get_output_path(f"layouts_{user.email}.zip")
            shutil.copy(zip_path, final_zip)

            logger.info(f"Final ZIP created at: {final_zip}")

        # Limpiar archivos temporales
        StorageManager.cleanup_file(golden_path)
        StorageManager.cleanup_file(metadata_path)

        return FileResponse(
            path=str(final_zip),
            filename="layouts.zip",
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=layouts.zip"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")