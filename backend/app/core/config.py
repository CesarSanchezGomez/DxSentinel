from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str = "SuccessFactors Parser"
    API_V1_STR: str = "/api/v1"

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "backend" / "storage" / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "backend" / "storage" / "outputs"

    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024

    class Config:
        case_sensitive = True


settings = Settings()

settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)