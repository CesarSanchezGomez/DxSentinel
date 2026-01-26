from pathlib import Path
from typing import Tuple, Optional
import uuid
from ..core.storage import StorageManager


class FileService:

    @staticmethod
    def save_uploaded_file(file_content: bytes, original_filename: str) -> Tuple[str, str]:
        file_id = str(uuid.uuid4())
        extension = Path(original_filename).suffix
        safe_filename = f"{file_id}{extension}"

        file_path = StorageManager.save_upload(file_content, safe_filename)

        return file_id, str(file_path)

    @staticmethod
    def get_file_path(file_id: str) -> Optional[Path]:
        return StorageManager.get_file_path_by_id(file_id)

    @staticmethod
    def cleanup_files(*file_ids: str):
        for file_id in file_ids:
            file_path = FileService.get_file_path(file_id)
            if file_path:
                StorageManager.cleanup_file(file_path)