# backend/app/api/v1/structure.py
import os
import shutil
from fastapi import APIRouter, BackgroundTasks, Form, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pathlib import Path
import json
import logging
from datetime import datetime
import tempfile
import csv
import io

from ...auth.dependencies import get_current_user
from ...core.config import get_settings

# Importar el orquestador de vstructure
from ....core.vstructure.orchestrator import ValidationOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)

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
        metadata_file = instance_path / version_to_use / f"document_{instance_id}.json"
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

@router.post("/validate")
async def validate_structure(
    golden_file: UploadFile = File(...),
    metadata_id: str = Form(...),
    version: str = Form("latest"),
    user=Depends(get_current_user)
):
    """Ejecuta validación estructural usando vstructure"""
    
    logger.info(f"User {user.email} validating structure for {metadata_id}, version: {version}")
    
    if not golden_file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser CSV")
    
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
    
    try:
        # Crear directorio persistente para esta validación
        validation_base = Path("backend/storage/reports") / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        validation_base.mkdir(parents=True, exist_ok=True)
        
        # Guardar CSV en directorio persistente
        csv_path = validation_base / "input_golden.csv"
        golden_content = await golden_file.read()
        with open(csv_path, 'wb') as f:
            f.write(golden_content)
        
        # Ejecutar validación con directorio persistente
        orchestrator = ValidationOrchestrator()
        results = orchestrator.execute_validation(
            instance_id=metadata_id,
            version=version_to_use,
            golden_record=str(csv_path),
            report_formats=["json", "csv"],
            output_dir=str(validation_base)  # <-- Directorio persistente
        )
        
        # Obtener rutas de archivos generados
        report_files = results.get("report_files", {})
        csv_report_path = report_files.get("csv")
        
        # Preparar respuesta con información de archivos
        response = {
            "success": True,
            "validation_id": results.get("execution_id"),
            "instance_id": metadata_id,
            "version": version_to_use,
            "summary": results.get("summary", {}),
            "execution_time": results.get("execution_time_seconds"),
            "report_files": {
                "csv": csv_report_path,
                "json": report_files.get("json")
            }
        }
        
        # Guardar mapeo validation_id -> directorio (para uso futuro)
        validation_map_path = Path("backend/storage/validation_map.json")
        validation_map = {}
        if validation_map_path.exists():
            with open(validation_map_path, 'r') as f:
                validation_map = json.load(f)
        
        validation_map[results.get("execution_id")] = {
            "directory": str(validation_base),
            "timestamp": datetime.now().isoformat(),
            "user": user.email
        }
        
        with open(validation_map_path, 'w') as f:
            json.dump(validation_map, f, indent=2)
        
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"Error in validation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en validación: {str(e)}")
    
@router.get("/download-csv/{validation_id}")
async def download_csv_report(
    validation_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user)
):
    """Descarga el archivo CSV generado y luego lo elimina"""
    
    validation_map_path = Path("backend/storage/validation_map.json")
    
    if not validation_map_path.exists():
        raise HTTPException(status_code=404, detail="No hay validaciones registradas")
    
    with open(validation_map_path, 'r') as f:
        validation_map = json.load(f)
    
    if validation_id not in validation_map:
        raise HTTPException(status_code=404, detail="Validación no encontrada")
    
    validation_info = validation_map[validation_id]
    base_dir = Path(validation_info["directory"])
    
    # Buscar archivo CSV
    csv_files = list(base_dir.glob("*validation*.csv"))
    if not csv_files:
        # Buscar cualquier CSV que no sea input
        csv_files = [f for f in base_dir.glob("*.csv") if "input_golden" not in f.name]
    
    if not csv_files:
        raise HTTPException(status_code=404, detail="Archivo CSV no encontrado")
    
    csv_path = csv_files[0]
    
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Archivo CSV no encontrado")
    
    # Preparar respuesta con archivo
    response = FileResponse(
        path=csv_path,
        filename=f"validation_report_{validation_id}.csv",
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=validation_report_{validation_id}.csv"
        }
    )
    
    # Agregar tarea para limpiar después de enviar
    background_tasks.add_task(
        cleanup_validation_files,
        validation_id=validation_id,
        file_path=csv_path,
        base_dir=base_dir
    )
    
    return response

def cleanup_validation_files(
    validation_id: str,
    file_path: Path,
    base_dir: Path
):
    """
    Limpia los archivos de validación después de la descarga.
    Se ejecuta en background después de enviar la respuesta.
    """
    try:
        # 1. Eliminar archivo específico descargado
        if file_path.exists():
            os.unlink(file_path)
            logger.info(f"Archivo eliminado: {file_path}")
        
        # 2. Verificar si quedan otros archivos en el directorio
        remaining_files = list(base_dir.glob("*"))
        
        # 3. Si solo queda el CSV de input o está vacío, eliminar todo
        if len(remaining_files) <= 1:  # Solo input_golden.csv o vacío
            # Eliminar JSON si existe
            json_files = list(base_dir.glob("*.json"))
            for json_file in json_files:
                if json_file.exists():
                    os.unlink(json_file)
            
            # Eliminar directorio si está vacío
            if base_dir.exists():
                shutil.rmtree(base_dir)
                logger.info(f"Directorio eliminado: {base_dir}")
            
            # 4. Eliminar del mapeo
            validation_map_path = Path("backend/storage/validation_map.json")
            if validation_map_path.exists():
                with open(validation_map_path, 'r') as f:
                    validation_map = json.load(f)
                
                if validation_id in validation_map:
                    del validation_map[validation_id]
                    
                    with open(validation_map_path, 'w') as f:
                        json.dump(validation_map, f, indent=2)
                    
                    logger.info(f"Validación {validation_id} eliminada del mapeo")
        
    except Exception as e:
        logger.error(f"Error en limpieza de archivos para {validation_id}: {str(e)}")