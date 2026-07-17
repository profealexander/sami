"""
server.py — Configuración del servidor y la infraestructura.

Separa lo que es del ENTORNO (server, BD, storage) de lo que es
del dominio (OCR, lógica de negocio).

Cada provider OCR ya tiene su propia config en ocr/*_provider.py.

NOTA SOBRE CONCURRENCIA (WORKERS / IO_POOL_SIZE):
Los defaults de WORKERS e IO_POOL_SIZE se calculan a partir de
os.cpu_count() para que el mismo .env funcione correctamente sin
cambios en VPS de distinta capacidad (1 vCore, 4 vCores, etc.).
Ambos siguen siendo sobreescribibles explícitamente vía variable
de entorno cuando se necesite un ajuste manual fino.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


@dataclass
class ServerConfig:
    """Configuración del servidor y la infraestructura."""

    # ── Entorno ──
    env: str = "development"  # development | production
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Concurrencia (derivada de os.cpu_count(), ver from_env) ──
    workers: int = 1
    io_pool_size: int = 8

    reload: bool = True
    log_level: str = "info"
    cors_origins: list | None = None

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
    s3_endpoint: str = ""  # Para Backblaze B2 o S3 compatible

    # Cloudinary (solo si storage_backend=cloudinary)
    cloudinary_url: str = ""

    # ── Rate limiting ──
    rate_limit: int = 100

    def __repr__(self) -> str:
        """Repr con secrets enmascarados."""

        def _mascara(valor: str, mostrar: int = 4) -> str:
            if not valor or len(valor) <= mostrar:
                return "***"
            return valor[:mostrar] + "***"

        return (
            f"ServerConfig(env={self.env}, host={self.host}, port={self.port}, "
            f"workers={self.workers}, io_pool_size={self.io_pool_size}, "
            f"storage={self.storage_backend}, db=_mascara, "
            f"s3_key={_mascara(self.s3_access_key)}, "
            f"cloudinary={_mascara(self.cloudinary_url, 10)})"
        )

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Crea ServerConfig a partir de variables de entorno y .env.

        WORKERS: por defecto, 1 proceso Uvicorn por vCore disponible en
        producción (1 en desarrollo). En un VPS de 1 core esto da
        WORKERS=1 automáticamente; en uno de 4 cores da WORKERS=4 sin
        tocar el .env.

        IO_POOL_SIZE: tamaño del ThreadPoolExecutor usado para llamadas
        I/O-bound (OCR.space, etc.). Escala más agresivo que los cores
        porque el cuello de botella ahí es espera de red, no CPU. Se
        limita a 32 como tope duro para no agotar RAM en VPS pequeños
        si el conteo de cores es alto.

        Levanta ValueError si la combinación RELOAD=true + WORKERS>1 es
        inválida (Uvicorn no soporta reload con múltiples workers), en
        vez de fallar de forma confusa al arrancar.
        """
        env = os.getenv("ENV", "development").strip().lower()
        is_prod = env == "production"
        cpu_count = os.cpu_count() or 1

        workers_default = cpu_count if is_prod else 1
        io_pool_default = min(32, cpu_count * 8)
        reload_default = not is_prod
        log_default = "warning" if is_prod else "info"

        # CORS: por defecto todo en dev, específico en prod
        cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
        cors_list = (
            ["*"] if cors_raw == "*" else [o.strip() for o in cors_raw.split(",")]
        )

        workers_final = int(os.getenv("WORKERS", str(workers_default)))
        reload_final = os.getenv("RELOAD", str(reload_default)).lower() == "true"

        if reload_final and workers_final > 1:
            raise ValueError(
                f"Configuración inválida: RELOAD=true es incompatible con WORKERS>1 "
                f"(WORKERS={workers_final}). Uvicorn no soporta reload con múltiples "
                f"workers. Setea RELOAD=false o WORKERS=1 en tu .env."
            )

        return cls(
            env=env,
            host=os.getenv(
                "HOST", "127.0.0.1" if env == "development" else "0.0.0.0"
            ).strip(),
            port=int(os.getenv("PORT", "8000")),
            workers=workers_final,
            io_pool_size=int(os.getenv("IO_POOL_SIZE", str(io_pool_default))),
            reload=reload_final,
            log_level=os.getenv("LOG_LEVEL", log_default).strip(),
            cors_origins=cors_list,
            database_url=os.getenv(
                "DATABASE_URL", "sqlite:///./comprobantes.db"
            ).strip(),
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
