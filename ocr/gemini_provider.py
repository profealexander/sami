"""
gemini_provider.py — Proveedor OCR usando Google Gemini API.

Configuración auto-contenida en GeminiConfig.
Parámetros desde .env.
"""

import io
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from config.logger import get_logger
from ocr.base import OCRProvider, OCRResult
from utils.exceptions import OCRError

logger = get_logger("gemini")


def _comprimir_imagen(imagen_path: Path, max_size: int = 1024) -> bytes:
    """Comprime imagen para reducir payload antes de enviar a API."""
    img = Image.open(imagen_path)
    # Reducir dimensiones si es muy grande
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    # Convertir a RGB si tiene canal alfa
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    # Guardar como JPEG comprimido
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue()

# Singleton para cliente Gemini (reutiliza conexión HTTP)
_gemini_client = None
_gemini_api_key = None


def _obtener_cliente_gemini(api_key: str):
    """Retorna cliente Gemini singleton, creándolo solo si cambia la API key."""
    global _gemini_client, _gemini_api_key
    from google import genai
    if _gemini_client is None or _gemini_api_key != api_key:
        _gemini_client = genai.Client(api_key=api_key)
        _gemini_api_key = api_key
    return _gemini_client


@dataclass
class GeminiConfig:
    """Parámetros ajustables de Gemini OCR."""
    api_key: str = ""
    model: str = "gemini-2.0-flash"
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "GeminiConfig":
        """Crea el provider desde variables de entorno y .env."""
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip(),
            timeout=int(os.getenv("GEMINI_TIMEOUT", "30")),
        )


SYSTEM_PROMPT = (
    "Eres un extractor de datos de comprobantes y tickets de venta.\n\n"
    "Analiza la imagen y extrae el texto completo del comprobante.\n"
    "Luego estructura la informacion en JSON con estos campos:\n"
    '  - "transfiere": nombre de la persona que transfiere o paga\n'
    '  - "no_comprobante": numero de ticket, factura o venta (opcional, si no aparece pon null)\n'
    '  - "monto": monto de la transaccion (ej: "150.00") (opcional, si no aparece pon null)\n'
    '  - "texto_completo": transcripcion completa y textual de todo el texto visible\n\n'
    "Reglas:\n"
    "- Si un campo no esta visible, pon null (no inventes valores)\n"
    "- Responde UNICAMENTE con el JSON, sin explicaciones ni markdown"
)


class GeminiProvider(OCRProvider):
    """OCR mediante Google Gemini API."""

    def __init__(self):
        self.config = GeminiConfig.from_env()

    @property
    def nombre(self) -> str:
        """Nombre del proveedor: gemini."""
        return "gemini"

    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        """Procesa la imagen con Gemini OCR y retorna los campos extraidos."""
        from google import genai

        if not self.config.api_key:
            logger.error("GEMINI_API_KEY no configurada en .env")
            raise OCRError(
                proveedor="gemini",
                causa="GEMINI_API_KEY no configurada en .env",
            )

        # Singleton: reutilizar cliente HTTP
        client = _obtener_cliente_gemini(self.config.api_key)
        imagen_path = Path(ruta_imagen)

        # Comprimir imagen si es muy grande (>1MB)
        imagen_bytes = imagen_path.read_bytes()
        if len(imagen_bytes) > 1_000_000:
            imagen_bytes = _comprimir_imagen(imagen_path)

        logger.debug(
            "Enviando imagen a Gemini: %s (%d bytes)",
            ruta_imagen, len(imagen_bytes),
        )

        # Detectar MIME type desde extensión
        from pathlib import Path
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime = mime_map.get(Path(ruta_imagen).suffix.lower(), "image/jpeg")

        try:
            response = client.models.generate_content(
                model=self.config.model,
                contents=[
                    SYSTEM_PROMPT,
                    genai.types.Part.from_bytes(
                        data=imagen_bytes,
                        mime_type=mime,
                    ),
                ],
            )
        except Exception as e:
            error_type = type(e).__name__
            logger.error("Gemini API error: %s — %s", error_type, str(e)[:300])
            raise OCRError(
                proveedor="gemini",
                causa=f"{error_type}: {str(e)[:200]}",
            ) from e

        texto_respuesta = response.text.strip()
        logger.debug(
            "Respuesta Gemini recibida (%d caracteres)", len(texto_respuesta)
        )
        datos = self._parsear_json(texto_respuesta)
        if not any(datos.get(k) for k in ("transfiere", "no_comprobante", "monto")):
            logger.warning(
                "Gemini no devolvio campos estructurados — texto=%s",
                texto_respuesta[:200],
            )

        return OCRResult(
            transfiere=datos.get("transfiere") or datos.get("cajero"),
            no_comprobante=datos.get("no_comprobante") or datos.get("no_venta"),
            monto=datos.get("monto"),
            texto_completo=datos.get("texto_completo", texto_respuesta),
            proveedor=self.nombre,
        )

    def _parsear_json(self, texto: str) -> dict:
        """Parsea el JSON devuelto por Gemini extrayendo solo los campos del comprobante."""
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

        logger.warning("No se pudo parsear JSON de respuesta Gemini")
        return {"texto_completo": texto}
