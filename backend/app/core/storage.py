from pathlib import Path
from typing import Optional
import shutil
from .config import settings


class StorageManager:

    @staticmethod
    def save_upload(file_content: bytes, filename: str) -> Path:
        file_path = settings.UPLOAD_DIR / filename
        with open(file_path, 'wb') as f:
            f.write(file_content)
        return file_path

    @staticmethod
    def get_output_path(filename: str) -> Path:
        return settings.OUTPUT_DIR / filename

    @staticmethod
    def cleanup_file(file_path: Path):
        if file_path.exists():
            file_path.unlink()

    @staticmethod
    def get_file(file_path: Path) -> Optional[bytes]:
        if file_path.exists():
            with open(file_path, 'rb') as f:
                return f.read()
        return None

    @staticmethod
    def get_file_path_by_id(file_id: str) -> Optional[Path]:
        for file in settings.UPLOAD_DIR.glob(f"{file_id}*"):
            return file
        return None