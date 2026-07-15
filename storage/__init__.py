"""
storage/__init__.py — Factoría de almacenamiento.

Uso:
    from storage import get_storage_backend
    backend = get_storage_backend()
    url = backend.guardar(imagen_bytes, "jpg")
"""

from config.server import server_config
from storage.base import StorageProvider

# Registro dinámico de backends
_REGISTRO_STORAGE: dict[str, type[StorageProvider]] = {}


def registrar_storage(nombre: str, clase: type[StorageProvider]):
    """Registra un backend de almacenamiento en la factoría."""
    _REGISTRO_STORAGE[nombre] = clase


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

    backend = server_config.storage_backend.lower()
    cls = _REGISTRO_STORAGE.get(backend)
    if not cls:
        raise ValueError(
            f"Storage backend desconocido: '{backend}'. "
            f"Valores disponibles: {', '.join(_REGISTRO_STORAGE.keys())}"
        )

    return cls()
