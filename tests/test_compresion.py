"""Tests para ocr/compresion.py"""

import io

import pytest
from PIL import Image

from ocr.compresion import comprimir_imagen


def _crear_imagen_bytes(
    ancho: int = 100,
    alto: int = 100,
    modo: str = "RGB",
    formato: str = "JPEG",
    quality: int = 95,
    color: tuple = (128, 200, 50),
) -> bytes:
    """Crea una imagen en memoria y retorna sus bytes."""
    img = Image.new(modo, (ancho, alto), color)
    buffer = io.BytesIO()
    img.save(buffer, format=formato, quality=quality)
    return buffer.getvalue()


def test_no_comprime_imagen_pequena():
    """Imagen dentro de ambos umbrales → sin cambios."""
    datos = _crear_imagen_bytes(100, 100, quality=50)
    resultado = comprimir_imagen(
        datos,
        activar_si_excede_bytes=1_000_000,
        activar_si_excede_dim=4000,
    )
    assert resultado is datos


def test_comprime_por_exceso_dimension():
    """Imagen que excede activar_si_excede_dim → redimensiona."""
    datos = _crear_imagen_bytes(5000, 4000, quality=50)
    resultado = comprimir_imagen(
        datos,
        max_dim=2000,
        activar_si_excede_bytes=0,
        activar_si_excede_dim=1000,
    )
    img = Image.open(io.BytesIO(resultado))
    assert img.width <= 2000
    assert img.height <= 2000


def test_comprime_por_exceso_bytes():
    """Imagen dentro de dimensión pero excede bytes → re-comprime."""
    datos = _crear_imagen_bytes(800, 600, quality=99, color=(255, 0, 0))
    resultado = comprimir_imagen(
        datos,
        max_dim=4000,
        quality=10,
        activar_si_excede_bytes=1,
        activar_si_excede_dim=4000,
    )
    assert len(resultado) < len(datos)


def test_convierte_rgba_a_rgb():
    """Imagen con canal alfa → se convierte a RGB."""
    datos = _crear_imagen_bytes(200, 200, modo="RGBA", formato="PNG")
    resultado = comprimir_imagen(
        datos,
        max_dim=4000,
        quality=50,
        activar_si_excede_bytes=0,
        activar_si_excede_dim=100,
    )
    img = Image.open(io.BytesIO(resultado))
    assert img.mode == "RGB"


def test_no_altera_aspect_ratio():
    """thumbnail mantiene el aspect ratio original."""
    datos = _crear_imagen_bytes(1600, 900, quality=50)
    resultado = comprimir_imagen(
        datos,
        max_dim=800,
        activar_si_excede_bytes=0,
        activar_si_excede_dim=1000,
    )
    img = Image.open(io.BytesIO(resultado))
    assert abs(img.width / img.height - 1600 / 900) < 0.01


def test_valores_toml_por_defecto():
    """Sin argumentos carga defaults de ocr/config.toml."""
    datos = _crear_imagen_bytes(100, 100, quality=50)
    resultado = comprimir_imagen(datos)
    assert resultado is datos
