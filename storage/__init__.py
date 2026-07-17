"""
storage/__init__.py — Factoría de almacenamiento.

Uso:
    from storage import get_storage_backend
    backend = get_storage_backend()
    url = backend.guardar(imagen_bytes, "jpg")
"""

from config import settings
from storage.base import StorageProvider
from config.logger import get_logger

logger = get_logger("storage.factory")

# Registro dinámico de backends
_REGISTRO_STORAGE: dict[str, type[StorageProvider]] = {}


def registrar_storage(nombre: str, clase: type[StorageProvider]):
    """Registra un backend de almacenamiento en la factoría."""
    _REGISTRO_STORAGE[nombre] = clase


def _validar_configuracion(backend: str):
    """Valida que las credenciales necesarias estén configuradas."""
    if backend == "s3":
        if not settings.s3_access_key:
            logger.warning("S3_ACCESS_KEY no configurada — S3 no funcionará")
        if not settings.s3_bucket:
            logger.warning("S3_BUCKET no configurada — S3 no funcionará")
    elif backend == "cloudinary":
        if not settings.cloudinary_url:
            logger.warning("CLOUDINARY_URL no configurada — Cloudinary no funcionará")


def get_storage_backend() -> StorageProvider:
    """Devuelve el backend de almacenamiento según STORAGE_BACKEND en .env."""
    # Auto-registrar si está vacío
    if not _REGISTRO_STORAGE:
        from storage.local import LocalStorageProvider
        from storage.s3 import S3StorageProvider
        from storage.cloudinary import CloudinaryStorageProvider

        registrar_storage("local", LocalStorageProvider)
        registrar_storage("s3", S3StorageProvider)
        registrar_storage("cloudinary", CloudinaryStorageProvider)

    backend = settings.storage_backend.lower()
    _validar_configuracion(backend)

    cls = _REGISTRO_STORAGE.get(backend)
    if not cls:
        raise ValueError(
            f"Storage backend desconocido: '{backend}'. "
            f"Valores disponibles: {', '.join(_REGISTRO_STORAGE.keys())}"
        )

    return cls()
