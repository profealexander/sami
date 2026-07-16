"""
settings.py — Configuración general de SAMI.

Solo contiene lo COMPARTIDO entre todos los módulos.
Cada proveedor OCR tiene su propia configuración auto-contenida
en su respectivo archivo (ocr/tesseract_provider.py, etc.).

Jerarquía de resolución:
1. Variable de entorno del sistema (Linux/Docker)
2. Archivo .env raíz
3. Archivo ocr/.env
4. Valores por defecto
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from config.common import PROJECT_ROOT

# Cargar configuración OCR antes de que Settings.load() lea las variables.
# override=False: vars del sistema y del .env raíz tienen prioridad.
load_dotenv(PROJECT_ROOT / "ocr" / ".env", override=False)


@dataclass
class Settings:
    """Configuración general del servidor SAMI."""

    # ── Archivos ──
    upload_dir: str = "uploads"

    # ── Selector de proveedor OCR ──
    # Valores: ocrspace, gemini, tesseract
    ocr_provider: str = "ocrspace"

    # ── Validación de uploads ──
    max_upload_size_mb: int = 10
    allowed_extensions: str = ".jpg,.jpeg,.png,.webp"

    # ── Logging ──
    log_file: str = ""

    @classmethod
    def load(cls) -> "Settings":
        """Carga Settings desde variables de entorno y .env."""
        return cls(
            upload_dir=os.getenv("UPLOAD_DIR", "uploads").strip(),
            ocr_provider=os.getenv("OCR_PROVIDER", "ocrspace").strip().lower(),
            max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")),
            allowed_extensions=os.getenv(
                "ALLOWED_EXTENSIONS", ".jpg,.jpeg,.png,.webp"
            ).strip(),
            log_file=os.getenv("LOG_FILE", "").strip(),
        )

    @property
    def upload_dir_abs(self) -> Path:
        """Ruta absoluta del directorio de uploads."""
        return PROJECT_ROOT / self.upload_dir


# ── Instancia global única ──
settings = Settings.load()
