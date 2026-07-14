"""
fallback.py — Proveedor OCR con fallback automático.

Prueba el proveedor primario (Gemini), y si falla (error de red,
cuota agotada, timeout, etc.) usa automáticamente el secundario (Tesseract).
"""

import traceback

from config.logger import get_logger
from ocr.base import OCRProvider, OCRResult

logger = get_logger("fallback")


class FallbackProvider(OCRProvider):
    """
    Envuelve dos proveedores: primario y fallback.

    extraer_campos() intenta con el primario. Si lanza cualquier excepción,
    registra el error completo y delega al fallback.
    """

    def __init__(self, primary: OCRProvider, fallback: OCRProvider):
        self._primary = primary
        self._fallback = fallback

    @property
    def nombre(self) -> str:
        return f"{self._primary.nombre}+{self._fallback.nombre}"

    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        try:
            return self._primary.extraer_campos(ruta_imagen)
        except Exception as e:
            logger.warning(
                "Fallback activado — %s falló, usando %s | error=%s",
                self._primary.nombre,
                self._fallback.nombre,
                str(e)[:300],
            )
            logger.debug("Traceback:\n%s", traceback.format_exc())
            return self._fallback.extraer_campos(ruta_imagen)
