"""
ocrspace_provider.py — Proveedor OCR usando OCR.space API.

Configuración auto-contenida en OCRSpaceConfig.
Parámetros desde .env.
"""

import base64
import os
import re
from dataclasses import dataclass
from pathlib import Path

import requests

from config.logger import get_logger
from ocr.base import OCRProvider, OCRResult
from utils.exceptions import OCRError

logger = get_logger("ocrspace")

API_URL = "https://api.ocr.space/parse/image"

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# ── Errores OCR comunes en meses (Tesseract a veces lee mal) ──
MESES_FALLBACK = {
    "jullo": "julio", "junlo": "junio", "julio": "julio",
    "enero": "enero", "febrero": "febrero", "marzo": "marzo",
    "abril": "abril", "mayo": "mayo", "agosto": "agosto",
    "setiembre": "septiembre", "octubre": "octubre",
    "noviembre": "noviembre", "diziembre": "diciembre",
}


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
            logger.error("OCRSPACE_API_KEY no configurada en .env")
            raise OCRError(
                proveedor="ocrspace",
                causa="OCRSPACE_API_KEY no configurada en .env",
            )

        with open(ruta_imagen, "rb") as f:
            imagen_b64 = base64.b64encode(f.read()).decode("utf-8")

        logger.debug(
            "Enviando a OCR.space: %s (%d KB)",
            ruta_imagen, len(imagen_b64) // 1024,
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
            return OCRResult(texto_completo="", proveedor=self.nombre)

        texto_completo = resultados[0].get("ParsedText", "")
        logger.debug(
            "OCR.space OK — %d caracteres extraidos", len(texto_completo)
        )
        campos = self._parsear_campos(texto_completo)

        return OCRResult(
            cajero=campos.get("cajero"),
            fecha=campos.get("fecha"),
            hora=campos.get("hora"),
            no_venta=campos.get("no_venta"),
            monto=campos.get("monto"),
            destinatario=campos.get("destinatario"),
            texto_completo=texto_completo.strip(),
            proveedor=self.nombre,
        )

    def _parsear_campos(self, texto: str) -> dict:
        """Extrae campos estructurados del texto OCR.

        Soporta tickets de venta y transferencias bancarias.
        """
        datos = {
            "cajero": None, "fecha": None, "hora": None,
            "no_venta": None, "monto": None, "destinatario": None,
        }

        for linea in texto.split("\n"):
            linea = linea.strip()
            if not linea:
                continue

            # ── Cajero (tickets) ──
            m = re.search(
                r'(?:CAJERO|ATENDIO|ATENDIÓ|CAJER@|VENDEDOR)\s*[\:\-]?\s*(.+)',
                linea, re.IGNORECASE,
            )
            if m and not datos["cajero"]:
                datos["cajero"] = m.group(1).strip()

            # ── Remitente (transferencias) ──
            m = re.search(r'^De\s+(.+)$', linea, re.IGNORECASE)
            if m and not datos["cajero"]:
                datos["cajero"] = m.group(1).strip()

            # ── Destinatario (transferencias) ──
            m = re.search(r'^A\s+(.+)$', linea, re.IGNORECASE)
            if m and not datos["destinatario"]:
                datos["destinatario"] = m.group(1).strip()

            # ── Monto ──
            m = re.search(r'\$\s*([0-9]+[\.\,]?[0-9]*)', linea)
            if m and not datos["monto"]:
                datos["monto"] = m.group(1)

            # ── Fecha numérica ──
            m = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})', linea)
            if m and not datos["fecha"]:
                d, mes, a = m.group(1), m.group(2), m.group(3)
                if 1 <= int(d) <= 31 and 1 <= int(mes) <= 12:
                    datos["fecha"] = f"{int(d):02d}/{int(mes):02d}/{a}"

            # ── Fecha textual ──
            m = re.search(
                r'El\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})',
                linea, re.IGNORECASE,
            )
            if m and not datos["fecha"]:
                dia, mes_str, anio = m.group(1), m.group(2).lower(), m.group(3)
                mes_num = MESES_ES.get(mes_str) or MESES_ES.get(MESES_FALLBACK.get(mes_str, ""))
                if mes_num:
                    datos["fecha"] = f"{int(dia):02d}/{mes_num:02d}/{anio}"

            # ── Hora ──
            m = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', linea)
            if m and not datos["hora"]:
                h, mi = int(m.group(1)), int(m.group(2))
                if 0 <= h <= 23 and 0 <= mi <= 59:
                    datos["hora"] = f"{h:02d}:{mi:02d}"

            # ── Número de comprobante ──
            if not datos["no_venta"]:
                for pat in [
                    r'(?:VENTA|TICKET|FACTURA|COMPROBANTE)\s*[\:\-]?\s*(\d[\d\-/]*)',
                    r'(?:No\.?|N°|NUMERO)\s*[\:\-]?\s*(\d[\d\-]*)',
                    r'N[°\*]\s*de\s+(?:comprobante|venta|ticket)\s*[\:\-]?\s*(\d[\d\-]*)',
                ]:
                    m = re.search(pat, linea, re.IGNORECASE)
                    if m:
                        datos["no_venta"] = m.group(1).strip()
                        break

        return datos
