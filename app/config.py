"""Proyecto Kantan - Configuración centralizada."""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Aplicación ──
    app_name: str = "Proyecto Kantan"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-key-cambiar-en-produccion"

    # ── Base de Datos ──
    database_url: str = "sqlite+aiosqlite:///./kantan.db"

    # ── JWT ──
    jwt_secret_key: str = "jwt-dev-secret-cambiar"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # ── Gemini API ──
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ── ChromaDB ──
    chroma_persist_dir: str = "./chroma_data"

    # ── Archivos ──
    upload_dir: str = "./uploads"
    generated_dir: str = "./generated"
    max_upload_size_mb: int = 20

    # ── Embeddings ──
    embedding_model: str = "text-embedding-004"
    chunk_size: int = 800
    chunk_overlap: int = 100

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def generated_path(self) -> Path:
        path = Path(self.generated_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Retorna la instancia de configuración (cacheada)."""
    return Settings()
