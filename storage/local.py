"""
local.py — Almacenamiento en disco local.

Configuración en .env:
    UPLOAD_DIR=uploads     (desde config/settings.py)
"""

import os

from config.logger import get_logger
from config.settings import settings, PROJECT_ROOT
from storage.base import StorageProvider

logger = get_logger("storage.local")


class LocalStorageProvider(StorageProvider):
    """Guarda imágenes en disco local (ruta relativa al proyecto)."""

    @property
    def nombre(self) -> str:
        """Nombre del backend: local."""
        return "local"

    def guardar(self, imagen_bytes: bytes, nombre_archivo: str) -> str:
        """Guarda la imagen en disco local y retorna ruta relativa."""
        ruta_relativa = os.path.join(settings.upload_dir, nombre_archivo)
        ruta_absoluta = PROJECT_ROOT / ruta_relativa
        ruta_absoluta.parent.mkdir(parents=True, exist_ok=True)
        ruta_absoluta.write_bytes(imagen_bytes)
        logger.info("Imagen guardada: %s (%d KB)", ruta_relativa, len(imagen_bytes) // 1024)
        return ruta_relativa
