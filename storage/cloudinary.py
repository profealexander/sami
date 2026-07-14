"""
cloudinary.py — Almacenamiento en Cloudinary.
Activo solo cuando STORAGE_BACKEND=cloudinary en .env.
"""

from config.logger import get_logger
from storage.base import StorageProvider
from config.server import server_config

logger = get_logger("storage.cloudinary")


class CloudinaryStorageProvider(StorageProvider):
    """Guarda imágenes en Cloudinary."""

    @property
    def nombre(self) -> str:
        """Nombre del backend: cloudinary."""
        return "cloudinary"

    def guardar(self, imagen_bytes: bytes, nombre_archivo: str) -> str:
        """Sube la imagen a Cloudinary y retorna su URL publica."""
        import cloudinary
        import cloudinary.uploader

        cloudinary.config(cloudinary_url=server_config.cloudinary_url)
        resultado = cloudinary.uploader.upload(
            imagen_bytes,
            public_id=f"comprobantes/{nombre_archivo.split('.')[0]}",
            resource_type="image",
        )
        url = resultado["secure_url"]
        logger.info("Imagen subida a Cloudinary: %s", url)
        return url
