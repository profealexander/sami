"""
local.py — Almacenamiento en disco local.

Configuración en .env:
    UPLOAD_DIR=uploads     (desde config/settings.py)
"""

import os
from pathlib import Path

from config.settings import settings, PROJECT_ROOT
from storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    """Guarda imágenes en disco local (ruta relativa al proyecto)."""

    @property
    def nombre(self) -> str:
        return "local"

    def guardar(self, imagen_bytes: bytes, nombre_archivo: str) -> str:
        ruta_relativa = os.path.join(settings.upload_dir, nombre_archivo)
        ruta_absoluta = PROJECT_ROOT / ruta_relativa
        ruta_absoluta.parent.mkdir(parents=True, exist_ok=True)
        ruta_absoluta.write_bytes(imagen_bytes)
        print(f"[SAMI] Imagen guardada en disco: {ruta_relativa}")
        return ruta_relativa
