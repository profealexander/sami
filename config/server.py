"""
server.py — Configuración del servidor y la infraestructura.

Separa lo que es del ENTORNO (server, BD, storage) de lo que es
del dominio (OCR, lógica de negocio).

Cada provider OCR ya tiene su propia config en ocr/*_provider.py.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

from config.common import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass
class ServerConfig:
    """Configuración del servidor y la infraestructura."""

    # ── Entorno ──
    env: str = "development"           # development | production
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = True
    log_level: str = "info"
    cors_origins: list = None

    # ── Base de datos ──
    database_url: str = "sqlite:///./comprobantes.db"
    db_pool_size: int = 10

    # ── Almacenamiento ──
    # Valores: local | s3 | cloudinary
    storage_backend: str = "local"

    # S3 (solo si storage_backend=s3)
    s3_bucket: str = ""
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_endpoint: str = ""              # Para Backblaze B2 o S3 compatible

    # Cloudinary (solo si storage_backend=cloudinary)
    cloudinary_url: str = ""

    # ── Rate limiting (placeholder) ──
    rate_limit: int = 100

    def __repr__(self) -> str:
        """Repr con secrets enmascarados."""
        def _mascara(valor: str, mostrar: int = 4) -> str:
            if not valor or len(valor) <= mostrar:
                return "***"
            return valor[:mostrar] + "***"

        return (
            f"ServerConfig(env={self.env}, host={self.host}, port={self.port}, "
            f"storage={self.storage_backend}, db=_mascara, "
            f"s3_key={_mascara(self.s3_access_key)}, "
            f"cloudinary={_mascara(self.cloudinary_url, 10)})"
        )

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Crea ServerConfig a partir de variables de entorno y .env."""
        env = os.getenv("ENV", "development").strip().lower()

        # En producción, por defecto más workers y sin reload
        is_prod = env == "production"
        workers_default = 4 if is_prod else 1
        reload_default = not is_prod
        log_default = "warning" if is_prod else "info"

        # CORS: por defecto todo en dev, específico en prod
        cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
        cors_list = ["*"] if cors_raw == "*" else [o.strip() for o in cors_raw.split(",")]

        return cls(
            env=env,
            host=os.getenv("HOST", "0.0.0.0").strip(),
            port=int(os.getenv("PORT", "8000")),
            workers=int(os.getenv("WORKERS", str(workers_default))),
            reload=os.getenv("RELOAD", str(reload_default)).lower() == "true",
            log_level=os.getenv("LOG_LEVEL", log_default).strip(),
            cors_origins=cors_list,

            database_url=os.getenv("DATABASE_URL", "sqlite:///./comprobantes.db").strip(),
            db_pool_size=int(os.getenv("DB_POOL_SIZE", "10")),

            storage_backend=os.getenv("STORAGE_BACKEND", "local").strip().lower(),

            s3_bucket=os.getenv("S3_BUCKET", "").strip(),
            s3_region=os.getenv("S3_REGION", "").strip(),
            s3_access_key=os.getenv("S3_ACCESS_KEY", "").strip(),
            s3_secret_key=os.getenv("S3_SECRET_KEY", "").strip(),
            s3_endpoint=os.getenv("S3_ENDPOINT", "").strip(),

            cloudinary_url=os.getenv("CLOUDINARY_URL", "").strip(),

            rate_limit=int(os.getenv("RATE_LIMIT", "100")),
        )

    @property
    def is_production(self) -> bool:
        """True si el entorno es production."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """True si el entorno es development."""
        return self.env == "development"


# ── Instancia global (se importa desde cualquier parte) ──
server_config = ServerConfig.from_env()
