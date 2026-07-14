"""
ocr/__init__.py — Factoría de proveedores OCR.

Uso:
    from ocr import get_ocr_engine
    engine = get_ocr_engine()
    resultado = engine.extraer_campos("uploads/foto.jpg")

Proveedores disponibles (según OCR_PROVIDER en .env):
    gemini    → Gemini con fallback a Tesseract
    tesseract → solo Tesseract local
    ocrspace  → OCR.space API
"""

from config.settings import settings
from ocr.base import OCRProvider


def get_ocr_engine() -> OCRProvider:
    """Devuelve el motor OCR según la configuración en .env."""
    provider = settings.ocr_provider

    if provider == "gemini":
        from ocr.gemini_provider import GeminiProvider
        from ocr.tesseract_provider import TesseractProvider
        from ocr.fallback import FallbackProvider
        return FallbackProvider(
            primary=GeminiProvider(),
            fallback=TesseractProvider(),
        )

    if provider == "tesseract":
        from ocr.tesseract_provider import TesseractProvider
        return TesseractProvider()

    if provider == "ocrspace":
        from ocr.ocrspace_provider import OCRSpaceProvider
        return OCRSpaceProvider()

    raise ValueError(
        f"Proveedor OCR desconocido: '{provider}'. "
        f"Valores disponibles: gemini, tesseract, ocrspace"
    )
