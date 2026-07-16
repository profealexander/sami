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

NOTA SOBRE EL SINGLETON:
get_ocr_engine() antes construía un FallbackProvider nuevo en cada
llamada, lo que reiniciaba el CircuitBreaker interno en cada request y
hacía que el umbral de "5 fallos consecutivos" documentado en
PROVEEDORES_OCR.md nunca se alcanzara en la práctica. Ahora la instancia
se cachea a nivel de módulo, así el conteo de fallos persiste mientras
el proceso viva. Esto asume un solo motor OCR por proceso Uvicorn (así
ya funciona hoy) — si en el futuro se corre con WORKERS>1, cada proceso
tiene su propio singleton y por lo tanto su propio circuit breaker
independiente, lo cual es aceptable (cada proceso protege su propia
tasa de llamadas al proveedor primario).
"""

import os
from config.settings import settings
from ocr.base import OCRProvider
from config.logger import get_logger

logger = get_logger("ocr.factory")

# Registro dinámico de proveedores
_REGISTRO_OCR: dict[str, type[OCRProvider]] = {}

# Singleton del motor OCR activo (incluye el circuit breaker si aplica)
_engine_instance: OCRProvider | None = None


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
    """Devuelve el motor OCR (singleton) según la configuración en .env.

    La primera llamada construye la instancia (y su circuit breaker, si
    aplica); las siguientes reutilizan la misma instancia, para que el
    estado interno (contador de fallos, timestamps de bloqueo) persista
    correctamente entre requests.
    """
    global _engine_instance
    if _engine_instance is not None:
        return _engine_instance

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
        _engine_instance = TesseractProvider()
        logger.info("Motor OCR inicializado (singleton): tesseract")
        return _engine_instance

    primary_cls = _REGISTRO_OCR.get(provider)
    if not primary_cls:
        raise ValueError(
            f"Proveedor OCR desconocido: '{provider}'. "
            f"Valores disponibles: {', '.join(_REGISTRO_OCR.keys())}"
        )

    _engine_instance = FallbackProvider(
        primary=primary_cls(),
        fallback=TesseractProvider(),
    )
    logger.info("Motor OCR inicializado (singleton): %s+tesseract", provider)
    return _engine_instance
