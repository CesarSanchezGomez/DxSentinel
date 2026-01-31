# backend/app/api/v1/endpoints/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from ....models.upload import UploadResponse
from ....services.file_service import FileService
from ....core.config import get_settings
from ....auth.dependencies import get_current_user
# NUEVO: Importar orquestador
from .....core.parsing.orchestrator import create_orchestrator

router = APIRouter()
settings = get_settings()


def validate_xml_type(content: bytes, expected_type: str) -> bool:
    """
    Valida que el XML sea del tipo esperado.

    Args:
        content: Contenido del archivo en bytes
        expected_type: 'sdm' o 'csf_sdm'

    Returns:
        bool: True si es válido
    """
    try:
        text_content = content.decode('utf-8', errors='ignore')

        if expected_type == 'sdm':
            return '<succession-data-model' in text_content
        elif expected_type == 'csf_sdm':
            return ('<country-specific-fields' in text_content and
                    '<format-group' in text_content)

        return False
    except Exception:
        return False


@router.post("/")
async def upload_file(
        file: UploadFile = File(...),
        file_type: str = None
):
    """
    Sube un archivo XML al servidor.

    Args:
        file: Archivo a subir
        file_type: Tipo esperado ('sdm' o 'csf_sdm') - opcional para validación
    """
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

    if file_type:
        if not validate_xml_type(content, file_type):
            error_messages = {
                'sdm': "El archivo no es un Succession Data Model válido. Debe contener '<succession-data-model'.",
                'csf_sdm': "El archivo no es un CSF Succession Data Model válido. Debe contener '<country-specific-fields' y '<format-group'."
            }
            raise HTTPException(
                status_code=400,
                detail=error_messages.get(file_type, "Tipo de archivo XML inválido")
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


@router.get("/list")
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


# IMPORTANTE: Este endpoint DEBE estar ANTES del endpoint /{file_id}
@router.get("/countries/{file_id}")
async def extract_countries(file_id: str):
    """
    Extrae la lista de países de un archivo CSF usando el orquestador.

    Args:
        file_id: ID del archivo CSF subido

    Returns:
        Lista de códigos de países encontrados
    """
    try:
        # Validar nombre de archivo
        if ".." in file_id or "/" in file_id or "\\" in file_id:
            raise HTTPException(
                status_code=400,
                detail="Nombre de archivo inválido"
            )

        # Obtener la ruta del archivo
        file_path = settings.UPLOAD_DIR / file_id

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Archivo no encontrado: {file_id}"
            )

        # NUEVO: Usar orquestador para extraer países
        orchestrator = create_orchestrator()
        
        # Parsear el CSF para obtener estructura normalizada
        result = orchestrator.parse_single_file(
            xml_path=file_path,
            source_name=f"CSF_{file_id}",
            origin='csf'
        )
        
        # Encontrar nodos país en la estructura normalizada
        countries = _find_country_codes_in_normalized(result)
        
        if not countries:
            raise HTTPException(
                status_code=400,
                detail="No se encontraron países en el archivo CSF"
            )

        return {
            "success": True,
            "countries": sorted(countries),
            "count": len(countries)
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al extraer países: {str(e)}"
        )


def _find_country_codes_in_normalized(normalized_model: dict) -> list:
    """
    Busca códigos de país en un modelo normalizado.
    """
    countries = set()
    
    def search_in_node(node: dict):
        tag = node.get("tag", "").lower()
        
        if 'country' in tag:
            # Intentar obtener código de país de varias formas
            tech_id = node.get("technical_id")
            if tech_id and len(tech_id) <= 3:
                countries.add(tech_id.upper())
            
            # Buscar en atributos
            attrs = node.get("attributes", {}).get("raw", {})
            possible_keys = ['id', 'countryCode', 'country-code', 'code']
            for key in possible_keys:
                if key in attrs:
                    value = attrs[key]
                    if value and len(str(value)) <= 3:
                        countries.add(str(value).upper())
        
        # Buscar recursivamente en hijos
        for child in node.get("children", []):
            search_in_node(child)
    
    # Buscar en la estructura
    structure = normalized_model.get("structure", {})
    search_in_node(structure)
    
    return list(countries)


# Este endpoint va AL FINAL porque captura cualquier /{file_id}
@router.delete("/{file_id}")
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