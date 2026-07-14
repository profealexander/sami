"""
settings.py — Configuración general de SAMI.

Solo contiene lo COMPARTIDO entre todos los módulos.
Cada proveedor OCR tiene su propia configuración auto-contenida
en su respectivo archivo (ocr/tesseract_provider.py, etc.).

Jerarquía de resolución:
1. Variable de entorno del sistema (Linux/Docker)
2. Archivo .env
3. Valores por defecto
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


# ── Ruta base del proyecto (D:\SAMI\ o /home/sami/) ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Cargar .env sin sobrescribir vars existentes
load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass
class Settings:
    """Configuración general del servidor SAMI."""

    # ── Servidor ──
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Archivos ──
    upload_dir: str = "uploads"

    # ── Selector de proveedor OCR ──
    # Valores: ocrspace, gemini, tesseract
    ocr_provider: str = "ocrspace"

    # ── Validación de uploads ──
    max_upload_size_mb: int = 10
    allowed_extensions: str = ".jpg,.jpeg,.png,.webp"

    # ── Logging ──
    log_level: str = "INFO"
    log_file: str = ""

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            host=os.getenv("HOST", "0.0.0.0").strip(),
            port=int(os.getenv("PORT", "8000")),
            upload_dir=os.getenv("UPLOAD_DIR", "uploads").strip(),
            ocr_provider=os.getenv("OCR_PROVIDER", "ocrspace").strip().lower(),
            max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")),
            allowed_extensions=os.getenv("ALLOWED_EXTENSIONS", ".jpg,.jpeg,.png,.webp").strip(),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
            log_file=os.getenv("LOG_FILE", "").strip(),
        )

    @property
    def upload_dir_abs(self) -> Path:
        """Ruta absoluta del directorio de uploads."""
        return PROJECT_ROOT / self.upload_dir


# ── Instancia global única ──
settings = Settings.load()
