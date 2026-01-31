# backend/app/core/config.py
from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "DxSentinel"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "backend" / "storage" / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "backend" / "storage" / "outputs"

    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB

    SUPABASE_URL: str
    SUPABASE_KEY: str
    ALLOWED_DOMAIN: str = "dxgrow.com"

    COOKIE_DOMAIN: str | None = None
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600  # 1 hora
    REFRESH_TOKEN_EXPIRE_SECONDS: int = 604800  # 7 días

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Crea una instancia única de Settings que se reutiliza.
    El decorador lru_cache asegura que solo se cree una vez.
    """
    return Settings()


settings = get_settings()

settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)