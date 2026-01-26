"""
Servicio para gestionar archivos subidos.
Implementación simple basada únicamente en filesystem.
No maneja usuarios ni metadata.
"""

from pathlib import Path
import uuid
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from ..core.config import get_settings

settings = get_settings()


class FileService:
    """Servicio para gestionar archivos subidos"""

    @staticmethod
    def save_uploaded_file(
        content: bytes,
        original_filename: str
    ) -> Tuple[str, Path]:
        """
        Guarda un archivo subido y retorna (file_id, file_path)

        Args:
            content: Contenido del archivo en bytes
            original_filename: Nombre original del archivo

        Returns:
            Tuple[str, Path]: (file_id, file_path)
        """

        file_extension = Path(original_filename).suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        file_id = f"{timestamp}_{unique_id}{file_extension}"
        file_path = settings.UPLOAD_DIR / file_id

        file_path.write_bytes(content)

        return file_id, file_path

    @staticmethod
    def get_file_path(file_id: str) -> Optional[Path]:
        """
        Obtiene la ruta de un archivo por su ID
        """

        file_path = settings.UPLOAD_DIR / file_id
        return file_path if file_path.exists() else None

    @staticmethod
    def delete_file(file_id: str) -> bool:
        """
        Elimina un archivo por su ID
        """

        file_path = settings.UPLOAD_DIR / file_id
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    @staticmethod
    def list_files() -> List[Dict]:
        """
        Lista todos los archivos XML subidos
        """

        files = []

        for file_path in settings.UPLOAD_DIR.glob("*.xml"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "file_id": file_path.name,
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created": stat.st_ctime
                })

        return files
