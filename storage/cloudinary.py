"""
cloudinary.py — Almacenamiento en Cloudinary.
Activo solo cuando STORAGE_BACKEND=cloudinary en .env.
"""

from storage.base import StorageProvider
from config.server import server_config


class CloudinaryStorageProvider(StorageProvider):
    """Guarda imágenes en Cloudinary."""

    @property
    def nombre(self) -> str:
        return "cloudinary"

    def guardar(self, imagen_bytes: bytes, nombre_archivo: str) -> str:
        import cloudinary
        import cloudinary.uploader

        cloudinary.config(cloudinary_url=server_config.cloudinary_url)
        resultado = cloudinary.uploader.upload(
            imagen_bytes,
            public_id=f"comprobantes/{nombre_archivo.split('.')[0]}",
            resource_type="image",
        )
        url = resultado["secure_url"]
        print(f"[SAMI] Imagen subida a Cloudinary: {url}")
        return url
