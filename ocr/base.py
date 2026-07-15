"""
base.py — Clase abstracta para proveedores OCR.

Cada proveedor debe implementar extraer_campos(ruta_imagen).
El método devuelve un OCRResult con los campos extraídos.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class OCRResult:
    """Resultado estandarizado del OCR, sin importar el proveedor.

    Campos comunes (siempre presentes):
      - cajero, fecha, hora, no_venta
      - texto_completo, proveedor

    Campos extendidos (según el tipo de comprobante):
      - monto: valor monetario detectado ($ XX.XX)
      - destinatario: persona/fondo destino (transferencias)
    """
    cajero: Optional[str] = None
    fecha: Optional[str] = None
    hora: Optional[str] = None
    no_venta: Optional[str] = None
    texto_completo: str = ""
    proveedor: str = ""

    # ── Campos extendidos (transferencias bancarias) ──
    monto: Optional[str] = None
    destinatario: Optional[str] = None


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
