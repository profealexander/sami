"""compresion.py — Compresión de imágenes para proveedores OCR.

Carga parámetros desde ocr/config.toml.
Usa Pillow para redimensionar y re-comprimir imágenes.
"""

import io
import tomllib
from pathlib import Path

from PIL import Image

_CONFIG_PATH = Path(__file__).resolve().parent / "config.toml"

with open(_CONFIG_PATH, "rb") as f:
    _cfg = tomllib.load(f)

_COMPRESION = _cfg.get("compresion", {})


def comprimir_imagen(
    datos: bytes,
    max_dim: int | None = None,
    quality: int | None = None,
    formato: str | None = None,
    optimizar: bool | None = None,
    activar_si_excede_bytes: int | None = None,
    activar_si_excede_dim: int | None = None,
) -> bytes:
    """Comprime una imagen en bytes si supera los umbrales configurados.

    Args:
        datos: Bytes de la imagen original.
        max_dim: Dimensión máxima (ancho/alto) tras redimensionar.
        quality: Calidad JPEG (1-100).
        formato: Formato de salida (JPEG, WEBP, PNG).
        optimizar: Optimización adicional de Pillow.
        activar_si_excede_bytes: Comprimir si el archivo supera este tamaño.
        activar_si_excede_dim: Redimensionar si algún lado supera este valor.

    Returns:
        Bytes comprimidos, o los originales si no supera ningún umbral.
    """
    if max_dim is None:
        max_dim = _COMPRESION.get("max_dim", 0)
    if quality is None:
        quality = _COMPRESION.get("quality", 85)
    if formato is None:
        formato = _COMPRESION.get("formato", "JPEG")
    if optimizar is None:
        optimizar = _COMPRESION.get("optimizar", True)
    if activar_si_excede_bytes is None:
        activar_si_excede_bytes = _COMPRESION.get("activar_si_excede_bytes", 0)
    if activar_si_excede_dim is None:
        activar_si_excede_dim = _COMPRESION.get("activar_si_excede_dim", 0)

    necesita_resize = False
    necesita_comprimir = False

    if activar_si_excede_dim > 0:
        img = Image.open(io.BytesIO(datos))
        necesita_resize = (
            img.width > activar_si_excede_dim or
            img.height > activar_si_excede_dim
        )

    if necesita_resize:
        necesita_comprimir = True
    elif activar_si_excede_bytes > 0:
        necesita_comprimir = len(datos) > activar_si_excede_bytes

    if not necesita_resize and not necesita_comprimir:
        return datos

    if not necesita_resize:
        img = Image.open(io.BytesIO(datos))

    if necesita_resize and max_dim > 0:
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format=formato, quality=quality, optimize=optimizar)
    return buffer.getvalue()
