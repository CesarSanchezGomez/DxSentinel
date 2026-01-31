from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from ....models.upload import UploadResponse
from ....services.file_service import FileService
from ....core.config import get_settings
from ....auth.dependencies import get_current_user
import xml.etree.ElementTree as ET

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


@router.get("/countries/{file_id}")
async def extract_countries(file_id: str):
    """
    Extrae la lista de países de un archivo CSF.

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
                detail="Archivo no encontrado"
            )

        # Leer y parsear el XML
        with open(file_path, 'rb') as f:
            content = f.read()

        # Decodificar contenido
        text_content = content.decode('utf-8', errors='ignore')

        # Validar que sea un CSF
        if not ('<country-specific-fields' in text_content and '<format-group' in text_content):
            raise HTTPException(
                status_code=400,
                detail="El archivo no es un CSF válido"
            )

        # Parsear XML
        root = ET.fromstring(content)

        # Buscar todos los elementos <country>
        countries = set()

        # Buscar en todo el árbol
        for elem in root.iter():
            # Eliminar namespace si existe
            tag = elem.tag
            if '}' in tag:
                tag = tag.split('}', 1)[1]

            # Verificar si es un elemento country
            if tag.lower() == 'country':
                country_id = elem.get('id')
                if country_id:
                    countries.add(country_id)

        # Convertir a lista ordenada
        country_list = sorted(list(countries))

        if not country_list:
            raise HTTPException(
                status_code=400,
                detail="No se encontraron países en el archivo CSF"
            )

        return {
            "success": True,
            "countries": country_list,
            "count": len(country_list)
        }

    except ET.ParseError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error al parsear XML: {str(e)}"
        )
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