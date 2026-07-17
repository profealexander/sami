"""
cloudinary.py — Almacenamiento en Cloudinary.
Activo solo cuando STORAGE_BACKEND=cloudinary en .env.
"""

import os
import tempfile

from config import settings
from config.logger import get_logger
from storage.base import StorageProvider
from utils.exceptions import StorageError

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

        try:
            cloudinary.config(cloudinary_url=settings.cloudinary_url)
            resultado = cloudinary.uploader.upload(
                imagen_bytes,
                public_id=f"comprobantes/{nombre_archivo.split('.')[0]}",
                resource_type="image",
            )
            url = resultado["secure_url"]
            logger.info("Imagen subida a Cloudinary: %s", url)
            return url
        except Exception as e:
            raise StorageError(
                backend="cloudinary", causa=f"Error subiendo a Cloudinary: {e}"
            ) from e

    def resolver_ruta(self, ruta: str) -> str:
        """Descarga imagen de Cloudinary a temporal para OCR."""
        import requests

        logger.info("Descargando imagen remota: %s", ruta)
        resp = requests.get(ruta, timeout=30)
        resp.raise_for_status()
        ext = ruta.split(".")[-1].split("?")[0] if "." in ruta else "jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(resp.content)
            tmp_name = tmp.name
        return tmp_name

    def limpiar_temporal(self, ruta: str) -> None:
        """Elimina archivo temporal descargado."""
        if ruta and os.path.exists(ruta):
            os.remove(ruta)
            logger.debug("Temporal eliminado: %s", ruta)
