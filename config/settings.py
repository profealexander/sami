"""
settings.py — Configuracion unificada con pydantic-settings.

Sigue la recomendacion oficial de FastAPI:
https://fastapi.tiangolo.com/advanced/settings/#pydantic-settings

Prioridad de variables (de mayor a menor):
1. Variables de entorno del sistema
2. .env raiz
3. Valores por defecto

Uso:
    from config import settings
    settings.port        # 7000 (desde .env)
    settings.database_url
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuración unificada del servidor SAMI."""

    # ── Servidor ──
    host: Optional[str] = None
    port: int = 8000
    env: str = "development"
    workers: Optional[int] = None
    io_pool_size: Optional[int] = None
    reload: Optional[bool] = None
    log_level: Optional[str] = None
    cors_origins: str = "*"

    # ── Base de datos ──
    database_url: str = "sqlite:///./comprobantes.db"
    db_pool_size: int = 10

    # ── Almacenamiento ──
    storage_backend: str = "local"
    s3_bucket: str = ""
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_endpoint: str = ""
    cloudinary_url: str = ""

    # ── Uploads ──
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10
    allowed_extensions: str = ".jpg,.jpeg,.png,.webp"

    # ── Rate limiting ──
    rate_limit: int = 100

    # ── Logging ──
    log_file: str = ""

    model_config = SettingsConfigDict(
        env_file=[".env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Retorna lista de orígenes CORS normalizada."""
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]

    @model_validator(mode="after")
    def _smart_defaults(self):
        """Aplica defaults inteligentes según el entorno (dev/prod)."""
        cpu = os.cpu_count() or 1
        prod = self.env == "production"

        if self.host is None:
            self.host = "0.0.0.0" if prod else "127.0.0.1"
        if self.workers is None:
            self.workers = cpu if prod else 1
        if self.io_pool_size is None:
            self.io_pool_size = min(32, cpu * 8)
        if self.reload is None:
            self.reload = not prod
        if self.log_level is None:
            self.log_level = "warning" if prod else "info"

        if self.reload and self.workers > 1:
            raise ValueError(
                "Configuracion invalida: RELOAD=true es incompatible con WORKERS>1"
                f" (WORKERS={self.workers}). Uvicorn no soporta reload con multiples "
                "workers. Setea RELOAD=false o WORKERS=1 en tu .env."
            )
        return self

    @property
    def is_production(self) -> bool:
        """Retorna True si el entorno es producción."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """Retorna True si el entorno es development."""
        return self.env == "development"

    @property
    def upload_dir_abs(self) -> Path:
        """Retorna la ruta absoluta del directorio de uploads."""
        return PROJECT_ROOT / self.upload_dir


@lru_cache
def get_settings() -> Settings:
    """Retorna el singleton Settings con valores cacheados."""
    return Settings()


settings = get_settings()
