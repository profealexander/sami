"""
ocrspace_provider.py — Proveedor OCR usando OCR.space API.

Configuración auto-contenida en OCRSpaceConfig.
Parámetros desde .env.
"""

import base64
import os
from dataclasses import dataclass

import requests

from config.logger import get_logger
from ocr.base import OCRProvider, OCRResult
from ocr.compresion import comprimir_imagen
from ocr.parsers import parsear_campos
from utils.exceptions import OCRError

logger = get_logger("ocrspace")

API_URL = "https://api.ocr.space/parse/image"


@dataclass
class OCRSpaceConfig:
    """Parámetros ajustables de OCR.space."""

    api_key: str = ""
    language: str = "spa"
    engine: int = 2
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "OCRSpaceConfig":
        """Crea el provider desde variables de entorno y .env."""
        return cls(
            api_key=os.getenv("OCRSPACE_API_KEY", "").strip(),
            language=os.getenv("OCRSPACE_LANGUAGE", "spa").strip(),
            engine=int(os.getenv("OCRSPACE_ENGINE", "2")),
            timeout=int(os.getenv("OCRSPACE_TIMEOUT", "30")),
        )


class OCRSpaceProvider(OCRProvider):
    """OCR mediante OCR.space API."""

    def __init__(self):
        self.config = OCRSpaceConfig.from_env()

    @property
    def nombre(self) -> str:
        """Nombre del proveedor: ocrspace."""
        return "ocrspace"

    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        """Procesa la imagen con Ocrspace OCR y retorna los campos extraidos."""
        if not self.config.api_key:
            logger.error("OCRSPACE_API_KEY no configurada en .env")
            raise OCRError(
                proveedor="ocrspace",
                causa="OCRSPACE_API_KEY no configurada en .env",
            )

        with open(ruta_imagen, "rb") as f:
            imagen_bytes = f.read()

        imagen_bytes = comprimir_imagen(imagen_bytes)

        imagen_b64 = base64.b64encode(imagen_bytes).decode("utf-8")

        logger.debug(
            "Enviando a OCR.space: %s (%d KB)",
            ruta_imagen,
            len(imagen_b64) // 1024,
        )

        try:
            respuesta = requests.post(
                API_URL,
                data={
                    "apikey": self.config.api_key,
                    "language": self.config.language,
                    "base64Image": f"data:image/jpeg;base64,{imagen_b64}",
                    "isOverlayRequired": False,
                    "OCREngine": self.config.engine,
                },
                timeout=self.config.timeout,
            )
            respuesta.raise_for_status()
        except requests.RequestException as e:
            logger.error("OCR.space error de red: %s", str(e)[:300])
            raise OCRError(
                proveedor="ocrspace",
                causa=f"Error HTTP: {str(e)[:200]}",
            ) from e

        datos = respuesta.json()

        if datos.get("IsErroredOnProcessing"):
            mensaje = datos.get("ErrorMessage", [{}])
            if isinstance(mensaje, list):
                mensaje = mensaje[0].get("ErrorMessage", str(datos))
            logger.error("OCR.space devolvio error: %s", mensaje)
            raise OCRError(proveedor="ocrspace", causa=str(mensaje))

        resultados = datos.get("ParsedResults", [])
        if not resultados:
            logger.warning("OCR.space no devolvio resultados")
            return OCRResult(proveedor=self.nombre)

        texto_completo = resultados[0].get("ParsedText", "")
        logger.debug("OCR.space OK — %d caracteres extraidos", len(texto_completo))
        resultado = parsear_campos(texto_completo)
        resultado.proveedor = self.nombre
        return resultado
