"""
gemini_provider.py — Proveedor OCR usando Google Gemini API.

Configuración auto-contenida en GeminiConfig.
Parámetros desde .env:

    GEMINI_API_KEY=           API key (obligatorio)
    GEMINI_MODEL=             Modelo (default: gemini-2.0-flash)
    GEMINI_TIMEOUT=30         Timeout en segundos
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from config.settings import PROJECT_ROOT
from ocr.base import OCRProvider, OCRResult


@dataclass
class GeminiConfig:
    """Parámetros ajustables de Gemini OCR."""
    api_key: str = ""
    model: str = "gemini-2.0-flash"
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "GeminiConfig":
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip(),
            timeout=int(os.getenv("GEMINI_TIMEOUT", "30")),
        )


SYSTEM_PROMPT = (
    "Eres un extractor de datos de comprobantes y tickets de venta.\n\n"
    "Analiza la imagen y extrae el texto completo del comprobante.\n"
    "Luego estructura la informacion en JSON con estos campos:\n"
    '  - "cajero": nombre de la persona que atendio o realizo la venta\n'
    '  - "fecha": fecha del comprobante en formato DD/MM/AAAA\n'
    '  - "hora": hora del comprobante en formato HH:MM\n'
    '  - "no_venta": numero de ticket, factura o venta (opcional, si no aparece pon null)\n'
    '  - "texto_completo": transcripcion completa y textual de todo el texto visible\n\n'
    "Reglas:\n"
    "- Si un campo no esta visible, pon null (no inventes valores)\n"
    "- Responde UNICAMENTE con el JSON, sin explicaciones ni markdown\n"
    "- La fecha debe estar en formato DD/MM/AAAA\n"
    "- La hora debe estar en formato HH:MM (24h)"
)


class GeminiProvider(OCRProvider):
    """OCR mediante Google Gemini API."""

    def __init__(self):
        self.config = GeminiConfig.from_env()

    @property
    def nombre(self) -> str:
        return "gemini"

    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        from google import genai

        if not self.config.api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada en .env")

        client = genai.Client(api_key=self.config.api_key)
        imagen_path = Path(ruta_imagen)
        imagen_bytes = imagen_path.read_bytes()

        response = client.models.generate_content(
            model=self.config.model,
            contents=[
                SYSTEM_PROMPT,
                genai.types.Part.from_bytes(
                    data=imagen_bytes,
                    mime_type="image/jpeg",
                ),
            ],
        )

        texto_respuesta = response.text.strip()
        datos = self._parsear_json(texto_respuesta)

        return OCRResult(
            cajero=datos.get("cajero"),
            fecha=datos.get("fecha"),
            hora=datos.get("hora"),
            no_venta=datos.get("no_venta"),
            texto_completo=datos.get("texto_completo", texto_respuesta),
            proveedor=self.nombre,
        )

    def _parsear_json(self, texto: str) -> dict:
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            pass

        m = re.search(r'```(?:json)?\s*([\s\S]*?)```', texto)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        m = re.search(r'\{[\s\S]*\}', texto)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        return {"texto_completo": texto}
