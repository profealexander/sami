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


class UploadValidator:
    """Validador de archivos con estado encapsulado."""

    def __init__(self, max_size_mb: int = 10, allowed_extensions: str = ".jpg,.jpeg,.png,.webp"):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = {
            ext.strip().lower()
            for ext in allowed_extensions.split(",")
            if ext.strip()
        }
        self.allowed_mimes = {"image/jpeg", "image/png", "image/webp"}

    def validar_tamano(self, contenido: bytes):
        """Valida que el archivo no exceda el tamaño máximo."""
        if len(contenido) > self.max_size_bytes:
            raise UploadValidationError(
                codigo=413,
                causa=f"Archivo demasiado grande ({len(contenido) // 1024}KB). Máximo: {self.max_size_mb}MB",
            )

    def validar_extension(self, filename: str):
        """Valida que la extensión esté permitida."""
        ext = Path(filename).suffix.lower()
        if ext not in self.allowed_extensions:
            raise UploadValidationError(
                codigo=422,
                causa=f"Extensión '{ext}' no permitida. Usar: {', '.join(sorted(self.allowed_extensions))}",
            )

    def validar_tipo_real(self, contenido: bytes):
        """Valida que el contenido real sea una imagen (magic bytes)."""
        try:
            img = Image.open(io.BytesIO(contenido))
            formato = img.format
            if formato:
                mime_real = f"image/{formato.lower()}"
                if mime_real not in self.allowed_mimes:
                    raise UploadValidationError(
                        codigo=422,
                        causa=f"Formato '{formato}' no permitido. Usar: JPEG, PNG o WebP",
                    )
        except UploadValidationError:
            raise
        except Exception:
            raise UploadValidationError(
                codigo=422,
                causa="El archivo no es una imagen válida",
            )

    def validar_content_type(self, content_type: str | None, filename: str):
        """Valida que el Content-Type reportado sea consistente con la extensión."""
        if not content_type:
            return  # No validar si no se reporta
        ext = Path(filename).suffix.lower()
        mime_esperado = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
        }.get(ext)
        if mime_esperado and content_type != mime_esperado:
            # Advertencia pero no bloquear — el usuario puede haber enviado el MIME incorrecto
            pass

    def validar_archivo(self, contenido: bytes, filename: str, content_type: str | None = None):
        """Ejecuta todas las validaciones en orden."""
        self.validar_tamano(contenido)
        self.validar_extension(filename)
        self.validar_tipo_real(contenido)
        if content_type:
            self.validar_content_type(content_type, filename)


# Instancia global (configurada al inicio)
_validator = UploadValidator()


def configure(max_size_mb: int, allowed_extensions: str):
    """Configura los límites desde settings.py."""
    global _validator
    _validator = UploadValidator(max_size_mb=max_size_mb, allowed_extensions=allowed_extensions)


def validar_tamano(contenido: bytes):
    """Valida que el archivo no exceda el tamaño máximo."""
    _validator.validar_tamano(contenido)


def validar_extension(filename: str):
    """Valida que la extensión esté permitida."""
    _validator.validar_extension(filename)


def validar_tipo_real(contenido: bytes):
    """Valida que el contenido real sea una imagen (magic bytes)."""
    _validator.validar_tipo_real(contenido)


def validar_archivo(contenido: bytes, filename: str, content_type: str | None = None):
    """Ejecuta todas las validaciones en orden."""
    _validator.validar_archivo(contenido, filename, content_type)


def validar_cliente_id(cliente_id: str):
    """Valida que el cliente_id tenga formato válido.

    Solo permite: letras, dígitos, guiones y guiones bajos.
    Longitud: 1-50 caracteres.

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
    caracteres_peligrosos = "/\\:*?\"<>|"
    for c in caracteres_peligrosos:
        nombre = nombre.replace(c, "_")

    return nombre
