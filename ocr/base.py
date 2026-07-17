"""
base.py — Clase abstracta para proveedores OCR.

Cada proveedor debe implementar extraer_campos(ruta_imagen).
El método devuelve un OCRResult con los campos extraídos.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class OCRResult(BaseModel):
    """Resultado estandarizado del OCR, sin importar el proveedor.

    Los nombres de campo coinciden con el ORM para poder usar model_dump().
    """

    transfiere: str | None = None
    no_comprobante: str | None = None
    monto: str | None = None
    destinatario: str | None = None
    texto_ocr_crudo: str | None = None
    proveedor: str = ""


class OCRProvider(ABC):
    """Interfaz que todo proveedor OCR debe implementar."""

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Nombre del proveedor OCR (implementar en subclase)."""
        ...

    @abstractmethod
    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        """Procesa la imagen y retorna campos extraidos (implementar en subclase)."""
        ...
