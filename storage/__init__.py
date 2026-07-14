"""
storage/__init__.py — Factoría de almacenamiento.

Uso:
    from storage import get_storage_backend
    backend = get_storage_backend()
    url = backend.guardar(imagen_bytes, "jpg")
"""

from config.server import server_config
from storage.base import StorageProvider


def get_storage_backend() -> StorageProvider:
    """Devuelve el backend de almacenamiento según STORAGE_BACKEND en .env."""
    backend = server_config.storage_backend

    if backend == "local":
        from storage.local import LocalStorageProvider
        return LocalStorageProvider()

    if backend == "s3":
        from storage.s3 import S3StorageProvider
        return S3StorageProvider()

    if backend == "cloudinary":
        from storage.cloudinary import CloudinaryStorageProvider
        return CloudinaryStorageProvider()

    raise ValueError(
        f"Storage backend desconocido: '{backend}'. "
        f"Valores disponibles: local, s3, cloudinary"
    )
