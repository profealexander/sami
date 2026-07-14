"""
fallback.py — Proveedor OCR con fallback automático.

Prueba el proveedor primario (Gemini), y si falla (error de red,
cuota agotada, timeout, etc.) usa automáticamente el secundario (Tesseract).
"""

from ocr.base import OCRProvider, OCRResult


class FallbackProvider(OCRProvider):
    """
    Envuelve dos proveedores: primario y fallback.

    extraer_campos() intenta con el primario. Si lanza cualquier excepción,
    registra el error y delega al fallback.
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
            error_msg = str(e)[:200]
            print(
                f"[SAMI] ⚠ Fallback: {self._primary.nombre} falló "
                f"({error_msg}), usando {self._fallback.nombre}"
            )
            return self._fallback.extraer_campos(ruta_imagen)
