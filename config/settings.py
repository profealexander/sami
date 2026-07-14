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
    # Valores: gemini, tesseract, ocrspace
    ocr_provider: str = "gemini"

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            host=os.getenv("HOST", "0.0.0.0").strip(),
            port=int(os.getenv("PORT", "8000")),
            upload_dir=os.getenv("UPLOAD_DIR", "uploads").strip(),
            ocr_provider=os.getenv("OCR_PROVIDER", "gemini").strip().lower(),
        )

    @property
    def upload_dir_abs(self) -> Path:
        """Ruta absoluta del directorio de uploads."""
        return PROJECT_ROOT / self.upload_dir


# ── Instancia global única ──
settings = Settings.load()
