"""
ocr/__init__.py — Factoría de proveedores OCR.

Uso:
    from ocr import get_ocr_engine
    engine = get_ocr_engine()
    resultado = engine.extraer_campos("uploads/foto.jpg")

Proveedores disponibles (según OCR_PROVIDER en .env):
    ocrspace  → OCR.space API (online) con fallback a Tesseract
    gemini    → Google Gemini API con fallback a Tesseract
    tesseract → solo Tesseract local (sin internet)
"""

import os
from config.settings import settings
from ocr.base import OCRProvider
from config.logger import get_logger

logger = get_logger("ocr.factory")

# Registro dinámico de proveedores
_REGISTRO_OCR: dict[str, type[OCRProvider]] = {}


def registrar_ocr(nombre: str, clase: type[OCRProvider]):
    """Registra un proveedor OCR en la factoría."""
    _REGISTRO_OCR[nombre] = clase


def _validar_configuracion(provider: str):
    """Valida que las API keys necesarias estén configuradas."""
    if provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY no configurada — Gemini OCR no funcionará")
    elif provider == "ocrspace" and not os.getenv("OCRSPACE_API_KEY"):
        logger.warning("OCRSPACE_API_KEY no configurada — OCR.space no funcionará")


def get_ocr_engine() -> OCRProvider:
    """Devuelve el motor OCR según la configuración en .env."""
    from ocr.tesseract_provider import TesseractProvider
    from ocr.fallback import FallbackProvider

    # Auto-registrar si está vacío
    if not _REGISTRO_OCR:
        from ocr.ocrspace_provider import OCRSpaceProvider
        from ocr.gemini_provider import GeminiProvider
        registrar_ocr("ocrspace", OCRSpaceProvider)
        registrar_ocr("gemini", GeminiProvider)
        registrar_ocr("tesseract", TesseractProvider)

    provider = settings.ocr_provider.lower()
    _validar_configuracion(provider)

    if provider == "tesseract":
        return TesseractProvider()

    primary_cls = _REGISTRO_OCR.get(provider)
    if not primary_cls:
        raise ValueError(
            f"Proveedor OCR desconocido: '{provider}'. "
            f"Valores disponibles: {', '.join(_REGISTRO_OCR.keys())}"
        )

    return FallbackProvider(
        primary=primary_cls(),
        fallback=TesseractProvider(),
    )
