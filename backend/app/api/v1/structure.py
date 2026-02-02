# backend/app/api/v1/structure.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from pathlib import Path
import json
import logging
from datetime import datetime
import tempfile
import zipfile
import shutil

from ...auth.dependencies import get_current_user
from ...core.storage import StorageManager
from ....core.generators.splitter.layout_splitter import LayoutSplitter  # CORREGIDO

router = APIRouter()
logger = logging.getLogger(__name__)

# Usar BASE_DIR desde config
from ...core.config import get_settings
settings = get_settings()

METADATA_BASE = settings.BASE_DIR / "backend" / "storage" / "metadata"


@router.get("/metadata/{instance_id}")
async def get_metadata(
    instance_id: str,
    version: str = Query("latest", description="Versión específica o 'latest'"),
    user=Depends(get_current_user)
):
    """Obtiene metadata de una instancia específica"""
    
    logger.info(f"User {user.email} requesting metadata for {instance_id}, version: {version}")
    
    instance_path = METADATA_BASE / instance_id
    
    if not instance_path.exists():
        raise HTTPException(status_code=404, detail=f"Instancia {instance_id} no encontrada")
    
    # Listar versiones disponibles
    versions = [d.name for d in instance_path.iterdir() if d.is_dir()]
    if not versions:
        raise HTTPException(status_code=404, detail=f"No hay versiones para {instance_id}")
    
    # Ordenar por fecha (última primero)
    versions.sort(reverse=True)
    
    # Determinar versión a usar
    if version == "latest":
        version_to_use = versions[0]
    else:
        if version not in versions:
            raise HTTPException(
                status_code=404, 
                detail=f"Versión {version} no encontrada. Versiones disponibles: {', '.join(versions)}"
            )
        version_to_use = version
    
    # Cargar metadata
    metadata_file = instance_path / version_to_use / f"metadata_{instance_id}.json"
    
    if not metadata_file.exists():
        # Intentar con document.json como fallback
        metadata_file = instance_path / version_to_use / "document.json"
        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail="Archivo de metadata no encontrado")
    
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Extraer información para el frontend
        response = {
            "id": instance_id,
            "version": version_to_use,
            "cliente": metadata.get("system_info", {}).get("parameters", {}).get("cliente"),
            "consultor": metadata.get("system_info", {}).get("parameters", {}).get("consultor"),
            "fecha": metadata.get("system_info", {}).get("creation_timestamp"),
            "path": str(metadata_file.relative_to(METADATA_BASE)),
            "raw": metadata,
            "available_versions": versions
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error loading metadata: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al cargar metadata: {str(e)}")


@router.get("/versions/{instance_id}")
async def get_versions(
    instance_id: str,
    user=Depends(get_current_user)
):
    """Obtiene lista de versiones disponibles para una instancia"""
    
    instance_path = METADATA_BASE / instance_id
    
    if not instance_path.exists():
        return []
    
    versions = [d.name for d in instance_path.iterdir() if d.is_dir()]
    versions.sort(reverse=True)  # Última primero
    
    return versions


@router.post("/load-golden-record")
async def load_golden_record(
    golden_file: UploadFile = File(...),
    metadata_id: str = Query(...),
    version: str = Query("latest"),
    user=Depends(get_current_user)
):
    """Procesa Golden Record para una versión específica de metadata"""
    
    logger.info(f"User {user.email} loading golden record for {metadata_id}, version: {version}")
    
    if not golden_file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Golden Record must be CSV")
    
    # Verificar que existe la metadata
    instance_path = METADATA_BASE / metadata_id
    if not instance_path.exists():
        raise HTTPException(status_code=404, detail=f"Instancia {metadata_id} no encontrada")
    
    # Determinar versión
    versions = [d.name for d in instance_path.iterdir() if d.is_dir()]
    if not versions:
        raise HTTPException(status_code=404, detail=f"No hay versiones para {metadata_id}")
    
    if version == "latest":
        version_to_use = versions[0]
    else:
        if version not in versions:
            raise HTTPException(
                status_code=404, 
                detail=f"Versión {version} no encontrada"
            )
        version_to_use = version
    
    # Cargar metadata
    metadata_file = instance_path / version_to_use / f"metadata_{metadata_id}.json"
    if not metadata_file.exists():
        # Intentar con document.json como fallback
        metadata_file = instance_path / version_to_use / "document.json"
        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail="Archivo de metadata no encontrado")
    
    try:
        # Guardar golden record temporalmente
        golden_content = await golden_file.read()
        golden_path = StorageManager.save_upload(
            golden_content, 
            f"golden_{user.email}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        # Procesar con LayoutSplitter (similar al endpoint de split)
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Processing golden record in temp dir: {temp_dir}")
            
            splitter = LayoutSplitter(str(metadata_file))
            layout_files = splitter.split_golden_record(str(golden_path), temp_dir)
            
            logger.info(f"Generated {len(layout_files)} layout files")
            
            if not layout_files:
                raise HTTPException(status_code=400, detail="No layouts were generated")
            
            # Crear ZIP
            zip_path = Path(temp_dir) / f"golden_record_{metadata_id}_{version_to_use}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for layout_file in layout_files:
                    zipf.write(layout_file, Path(layout_file).name)
                    logger.info(f"Added to ZIP: {Path(layout_file).name}")
            
            # Copiar a outputs
            final_zip = StorageManager.get_output_path(
                f"golden_record_{metadata_id}_{version_to_use}_{user.email}.zip"
            )
            shutil.copy(zip_path, final_zip)
            
            logger.info(f"Final ZIP created at: {final_zip}")
        
        # Limpiar archivo temporal
        StorageManager.cleanup_file(golden_path)
        
        return FileResponse(
            path=str(final_zip),
            filename=f"golden_record_{metadata_id}_{version_to_use}.zip",
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=golden_record_{metadata_id}_{version_to_use}.zip"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing golden record: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing golden record: {str(e)}")