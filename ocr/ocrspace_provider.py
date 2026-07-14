"""
ocrspace_provider.py — Proveedor OCR usando OCR.space API.

Configuración auto-contenida en OCRSpaceConfig.
Parámetros desde .env:

    OCRSPACE_API_KEY=          API key (obligatorio)
    OCRSPACE_LANGUAGE=spa      Idioma
    OCRSPACE_ENGINE=2          Engine OCR (1=legacy, 2=moderno)
    OCRSPACE_TIMEOUT=30        Timeout en segundos
"""

import base64
import os
import re
from dataclasses import dataclass
from pathlib import Path

import requests

from ocr.base import OCRProvider, OCRResult


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
        return "ocrspace"

    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        if not self.config.api_key:
            raise RuntimeError("OCRSPACE_API_KEY no configurada en .env")

        with open(ruta_imagen, "rb") as f:
            imagen_b64 = base64.b64encode(f.read()).decode("utf-8")

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

        datos = respuesta.json()

        if datos.get("IsErroredOnProcessing"):
            mensaje = datos.get("ErrorMessage", [{}])
            if isinstance(mensaje, list):
                mensaje = mensaje[0].get("ErrorMessage", str(datos))
            raise RuntimeError(f"OCR.space error: {mensaje}")

        resultados = datos.get("ParsedResults", [])
        if not resultados:
            return OCRResult(texto_completo="", proveedor=self.nombre)

        texto_completo = resultados[0].get("ParsedText", "")
        campos = self._parsear_campos(texto_completo)

        return OCRResult(
            cajero=campos.get("cajero"),
            fecha=campos.get("fecha"),
            hora=campos.get("hora"),
            no_venta=campos.get("no_venta"),
            texto_completo=texto_completo.strip(),
            proveedor=self.nombre,
        )

    def _parsear_campos(self, texto: str) -> dict:
        datos = {"cajero": None, "fecha": None, "hora": None, "no_venta": None}
        for linea in texto.split("\n"):
            linea = linea.strip()
            if not linea:
                continue
            m = re.search(r'(?:CAJERO|ATENDIO|ATENDIÓ|CAJER@|VENDEDOR)\s*[:\-]?\s*(.+)', linea, re.IGNORECASE)
            if m and not datos["cajero"]:
                datos["cajero"] = m.group(1).strip()
            m = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})', linea)
            if m and not datos["fecha"]:
                d, mes, a = m.group(1), m.group(2), m.group(3)
                if 1 <= int(d) <= 31 and 1 <= int(mes) <= 12:
                    datos["fecha"] = f"{int(d):02d}/{int(mes):02d}/{a}"
            m = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', linea)
            if m and not datos["hora"]:
                h, mi = int(m.group(1)), int(m.group(2))
                if 0 <= h <= 23 and 0 <= mi <= 59:
                    datos["hora"] = f"{h:02d}:{mi:02d}"
            if not datos["no_venta"]:
                for pat in [
                    r'(?:VENTA|TICKET|FACTURA|COMPROBANTE)\s*[:\-]?\s*(\d[\d\-/]*)',
                    r'(?:No\.?|N°|NUMERO)\s*[:\-]?\s*(\d[\d\-]*)',
                ]:
                    m = re.search(pat, linea, re.IGNORECASE)
                    if m:
                        datos["no_venta"] = m.group(1).strip()
                        break
        return datos
