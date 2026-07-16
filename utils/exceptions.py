"""
exceptions.py — Excepciones personalizadas de SAMI.

Permiten identificar el origen del error (OCR vs Storage vs Upload)
sin depender de excepciones genéricas.
"""


class SAMIError(Exception):
    """Error base del sistema SAMI."""

    def __init__(self, mensaje: str, causa: str = ""):
        self.mensaje = mensaje
        self.causa = causa
        super().__init__(f"{mensaje}" + (f" | Causa: {causa}" if causa else ""))


class OCRError(SAMIError):
    """Error en el proceso de OCR.

    Attributes:
        proveedor: Nombre del proveedor que falló (gemini, tesseract, ocrspace)
        causa: Descripción del error técnico
    """

    def __init__(self, proveedor: str, causa: str = ""):
        self.proveedor = proveedor
        super().__init__(
            mensaje=f"Error OCR con proveedor '{proveedor}'",
            causa=causa,
        )


class StorageError(SAMIError):
    """Error en el almacenamiento de imágenes.

    Attributes:
        backend: Nombre del backend (local, s3, cloudinary)
        causa: Descripción del error técnico
    """

    def __init__(self, backend: str, causa: str = ""):
        self.backend = backend
        super().__init__(
            mensaje=f"Error de almacenamiento con backend '{backend}'",
            causa=causa,
        )


class UploadValidationError(SAMIError):
    """Error de validación del archivo subido.

    Attributes:
        codigo: Código HTTP sugerido (413, 415, 422)
        causa: Descripción del error
    """

    def __init__(self, codigo: int, causa: str = ""):
        self.codigo = codigo
        super().__init__(
            mensaje=f"Archivo inválido (HTTP {codigo})",
            causa=causa,
        )
