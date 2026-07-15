"""
upload_validator.py — Validación de archivos subidos.

Protege el servidor contra:
- Archivos demasiado grandes (DoS)
- Tipos MIME no permitidos (ejecutables, scripts)
- Extensiones con caracteres peligrosos (path traversal)

Configurable via .env:
    MAX_UPLOAD_SIZE_MB=10       # Tamaño máximo en MB
    ALLOWED_EXTENSIONS=.jpg,.jpeg,.png,.webp
"""

import io
import re
from pathlib import Path

from PIL import Image

from utils.exceptions import UploadValidationError

# Regex pre-compilado para validación de cliente_id
RE_CLIENTE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")

# ── Valores por defecto (se sobreescriben desde settings) ──
_MAX_SIZE_MB = 10
_MAX_SIZE_BYTES = _MAX_SIZE_MB * 1024 * 1024
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}


def configure(max_size_mb: int, allowed_extensions: str):
    """Configura los límites desde settings.py."""
    global _MAX_SIZE_MB, _MAX_SIZE_BYTES, _ALLOWED_EXTENSIONS
    _MAX_SIZE_MB = max_size_mb
    _MAX_SIZE_BYTES = max_size_mb * 1024 * 1024
    _ALLOWED_EXTENSIONS = {
        ext.strip().lower()
        for ext in allowed_extensions.split(",")
        if ext.strip()
    }


def validar_archivo(contenido: bytes, filename: str) -> None:
    """Valida tamaño, extensión y tipo MIME real del archivo.

    Args:
        contenido: Bytes del archivo subido
        filename: Nombre original del archivo

    Raises:
        UploadValidationError: si alguna validación falla
    """
    validar_tamano(contenido)
    validar_extension(filename)
    validar_tipo_real(contenido)


def validar_tamano(contenido: bytes) -> None:
    """Valida que el archivo no exceda el tamaño máximo."""
    if len(contenido) > _MAX_SIZE_BYTES:
        raise UploadValidationError(
            codigo=413,
            causa=(
                f"El archivo pesa {len(contenido) / 1024 / 1024:.1f} MB, "
                f"máximo permitido: {_MAX_SIZE_MB} MB"
            ),
        )


def validar_extension(filename: str) -> None:
    """Valida que la extensión del archivo esté permitida."""
    if not filename or "." not in filename:
        raise UploadValidationError(
            codigo=422,
            causa="El archivo no tiene extensión",
        )

    ext = f".{filename.rsplit('.', 1)[-1].lower()}"
    if ext not in _ALLOWED_EXTENSIONS:
        raise UploadValidationError(
            codigo=415,
            causa=(
                f"Extensión '{ext}' no permitida. "
                f"Permitidas: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
            ),
        )


def validar_tipo_real(contenido: bytes) -> None:
    """Valida el tipo MIME real leyendo los magic bytes.

    Usa PIL para detectar el formato real,
    independientemente de la extensión del archivo.
    """
    try:
        detected_format = Image.open(io.BytesIO(contenido)).format
    except Exception:
        raise UploadValidationError(
            codigo=415,
            causa="El archivo no es una imagen válida (no se detectó formato)",
        )

    mime_map = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
    }
    mime = mime_map.get(detected_format)
    if mime not in _ALLOWED_MIMES:
        raise UploadValidationError(
            codigo=415,
            causa=(
                f"Tipo de imagen '{detected_format}' no permitido. "
                f"Permitidos: {', '.join(_ALLOWED_MIMES)}"
            ),
        )


def validar_cliente_id(cliente_id: str) -> None:
    """Valida que el cliente_id tenga formato permitido.

    Solo letras, dígitos, guiones y guiones bajos, de 1 a 50 caracteres.

    Raises:
        UploadValidationError: si el formato es inválido (HTTP 422)
    """
    if not RE_CLIENTE_ID.fullmatch(cliente_id):
        raise UploadValidationError(
            codigo=422,
            causa=(
                "cliente_id solo puede contener letras, dígitos, guiones "
                "y guiones bajos, entre 1 y 50 caracteres"
            ),
        )


def sanitizar_filename(filename: str) -> str:
    """Limpia el nombre de archivo para prevenir path traversal.

    Elimina caracteres peligrosos y asegura que sea solo un nombre
    de archivo, no una ruta.
    """
    # Tomar solo el nombre base (sin directorios)
    nombre = Path(filename).name

    # Reemplazar caracteres peligrosos
    caracteres_peligrosos = "/\:*?\"<>|"
    for c in caracteres_peligrosos:
        nombre = nombre.replace(c, "_")

    return nombre
