"""
base.py — Clase abstracta para proveedores OCR.

Cada proveedor debe implementar extraer_campos(ruta_imagen).
El método devuelve un diccionario con las llaves:
  - cajero (str o None)
  - fecha (str o None)
  - hora (str o None)
  - no_venta (str o None, opcional)
  - texto_completo (str, texto OCR completo)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class OCRResult:
    """Resultado estandarizado del OCR, sin importar el proveedor."""
    cajero: Optional[str] = None
    fecha: Optional[str] = None
    hora: Optional[str] = None
    no_venta: Optional[str] = None
    texto_completo: str = ""
    proveedor: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class OCRProvider(ABC):
    """Interfaz que todo proveedor OCR debe implementar."""

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Nombre del proveedor (gemini, easyocr, etc.)"""
        ...

    @abstractmethod
    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        """
        Procesa una imagen y extrae los campos del comprobante.

        Args:
            ruta_imagen: Ruta absoluta o relativa a la imagen.

        Returns:
            OCRResult con los campos extraídos.
        """
        ...
