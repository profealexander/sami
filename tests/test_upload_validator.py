"""
Tests para utils/upload_validator.py
"""

import io
import pytest
from PIL import Image

from utils.upload_validator import (
    validar_archivo,
    validar_tamano,
    validar_extension,
    validar_tipo_real,
    sanitizar_filename,
    configure,
)
from utils.exceptions import UploadValidationError


def crear_imagen_bytes(formato: str = "JPEG") -> bytes:
    """Crea una imagen válida en memoria."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format=formato)
    return buffer.getvalue()


def crear_bytes_invalidos() -> bytes:
    """Bytes que NO son imagen."""
    return b"Esto no es una imagen"


class TestValidarTamano:
    def test_archivo_dentro_del_limite(self):
        configure(max_size_mb=10, allowed_extensions=".jpg,.png")
        contenido = b"x" * (5 * 1024 * 1024)
        validar_tamano(contenido)

    def test_archivo_excede_limite(self):
        configure(max_size_mb=1, allowed_extensions=".jpg,.png")
        contenido = b"x" * (2 * 1024 * 1024)
        with pytest.raises(UploadValidationError) as exc_info:
            validar_tamano(contenido)
        assert exc_info.value.codigo == 413


class TestValidarExtension:
    def test_extension_permitida(self):
        configure(max_size_mb=10, allowed_extensions=".jpg,.jpeg,.png,.webp")
        validar_extension("foto.jpg")
        validar_extension("imagen.PNG")

    def test_extension_no_permitida(self):
        configure(max_size_mb=10, allowed_extensions=".jpg,.png")
        with pytest.raises(UploadValidationError) as exc_info:
            validar_extension("archivo.exe")
        assert exc_info.value.codigo == 415


class TestValidarTipoReal:
    def test_jpeg_valido(self):
        configure(max_size_mb=10, allowed_extensions=".jpg,.jpeg,.png,.webp")
        contenido = crear_imagen_bytes("JPEG")
        validar_tipo_real(contenido)

    def test_archivo_no_es_imagen(self):
        configure(max_size_mb=10, allowed_extensions=".jpg,.png")
        contenido = crear_bytes_invalidos()
        with pytest.raises(UploadValidationError) as exc_info:
            validar_tipo_real(contenido)
        assert exc_info.value.codigo == 415


class TestSanitizarFilename:
    def test_elimina_rutas_unix(self):
        assert sanitizar_filename("/etc/passwd") == "passwd"

    def test_elimina_rutas_windows(self):
        assert sanitizar_filename("C:/Users/foto.jpg") == "foto.jpg"

    def test_reemplaza_caracteres_peligrosos(self):
        resultado = sanitizar_filename("archivo<>.txt")
        assert "<" not in resultado
        assert ">" not in resultado
