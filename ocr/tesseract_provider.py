"""
tesseract_provider.py — Proveedor OCR usando Tesseract local.

Configuración auto-contenida en TesseractConfig.
Parámetros editables desde .env sin tocar código:

    TESSERACT_CMD=          Ruta del ejecutable (auto-detecta si se omite)
    TESSERACT_LANG=spa      Idioma
    TESSERACT_SCALE=2.0     Escalar imagen antes de OCR (mejora precisión)
    TESSERACT_THRESHOLD=0   Binarización: 0=Otsu automático, 1-254=manual, 255=sin binarizar
    TESSERACT_DENOISE=true  Eliminar ruido con filtro mediana
    TESSERACT_PSM=3         Page segmentation mode de Tesseract
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import pytesseract
from PIL import Image, ImageFilter, ImageEnhance

from ocr.base import OCRProvider, OCRResult


# ── Rutas por defecto ──
RUTAS_POR_DEFECTO = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


@dataclass
class TesseractConfig:
    """Parámetros ajustables de Tesseract OCR."""
    cmd: str = ""
    lang: str = "spa"
    scale: float = 2.0
    threshold: int = 0       # 0 = Otsu automático
    denoise: bool = True
    psm: int = 3

    @classmethod
    def from_env(cls) -> "TesseractConfig":
        cfg = cls(
            cmd=os.getenv("TESSERACT_CMD", "").strip(),
            lang=os.getenv("TESSERACT_LANG", "spa").strip(),
            scale=float(os.getenv("TESSERACT_SCALE", "2.0")),
            threshold=int(os.getenv("TESSERACT_THRESHOLD", "0")),
            denoise=os.getenv("TESSERACT_DENOISE", "true").lower() == "true",
            psm=int(os.getenv("TESSERACT_PSM", "3")),
        )
        # Auto-detectar ruta si no se especificó
        if not cfg.cmd or not os.path.exists(cfg.cmd):
            for ruta in RUTAS_POR_DEFECTO:
                if os.path.exists(ruta):
                    cfg.cmd = ruta
                    break
        return cfg


class TesseractProvider(OCRProvider):
    """OCR mediante Tesseract con preprocesamiento de imagen."""

    def __init__(self):
        self.config = TesseractConfig.from_env()
        if self.config.cmd and os.path.exists(self.config.cmd):
            pytesseract.pytesseract.tesseract_cmd = self.config.cmd

    @property
    def nombre(self) -> str:
        return "tesseract"

    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        if not self.config.cmd or not os.path.exists(self.config.cmd):
            return OCRResult(texto_completo="", proveedor=self.nombre)

        # 1. Abrir imagen
        img = Image.open(ruta_imagen)

        # 2. Preprocesar
        img = self._preprocesar(img)

        # 3. OCR
        config_str = f"--psm {self.config.psm}"
        texto_completo = pytesseract.image_to_string(
            img, lang=self.config.lang, config=config_str
        )

        # 4. Parsear campos
        campos = self._parsear_campos(texto_completo)

        return OCRResult(
            cajero=campos.get("cajero"),
            fecha=campos.get("fecha"),
            hora=campos.get("hora"),
            no_venta=campos.get("no_venta"),
            texto_completo=texto_completo.strip(),
            proveedor=self.nombre,
        )

    def _preprocesar(self, img: Image.Image) -> Image.Image:
        """Preprocesa la imagen para mejorar la precisión de Tesseract."""
        # Escalar (mejora dramática en fotos de celular)
        if self.config.scale != 1.0:
            w, h = img.size
            img = img.resize(
                (int(w * self.config.scale), int(h * self.config.scale)),
                Image.LANCZOS
            )

        # Convertir a grises
        img = img.convert("L")

        # Eliminar ruido con filtro mediana
        if self.config.denoise:
            img = img.filter(ImageFilter.MedianFilter(3))

        # Binarización (thresholding)
        if self.config.threshold == 0:
            # Otsu automático: usar un threshold adaptativo
            # Simple: calcular el promedio como threshold
            pixeles = list(img.getdata())
            umbral = sum(pixeles) // len(pixeles)
            img = img.point(lambda p: 255 if p > umbral else 0)
        elif self.config.threshold < 255:
            img = img.point(lambda p: 255 if p > self.config.threshold else 0)
        # threshold=255 => sin binarizar (escala de grises pura)

        return img

    def _parsear_campos(self, texto: str) -> dict:
        datos = {"cajero": None, "fecha": None, "hora": None, "no_venta": None}

        for linea in texto.split("\n"):
            linea = linea.strip()
            if not linea:
                continue

            m = re.search(
                r'(?:CAJERO|ATENDIO|ATENDIÓ|CAJER@|VENDEDOR)\s*[:\-]?\s*(.+)',
                linea, re.IGNORECASE
            )
            if m and not datos["cajero"]:
                datos["cajero"] = m.group(1).strip()

            m = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})', linea)
            if m and not datos["fecha"]:
                d, mes, a = m.group(1), m.group(2), m.group(3)
                if 1 <= int(d) <= 31 and 1 <= int(mes) <= 12:
                    datos["fecha"] = f"{int(d):02d}/{int(mes):02d}/{a}"

            m = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', linea)
            if m and not datos["hora"]:
                h, mi = int(m.group(1)), int(m.group(2))
                if 0 <= h <= 23 and 0 <= mi <= 59:
                    datos["hora"] = f"{h:02d}:{mi:02d}"

            if not datos["no_venta"]:
                for pat in [
                    r'(?:VENTA|TICKET|FACTURA|COMPROBANTE)\s*[:\-]?\s*(\d[\d\-/]*)',
                    r'(?:No\.?|N°|NUMERO)\s*[:\-]?\s*(\d[\d\-]*)',
                ]:
                    m = re.search(pat, linea, re.IGNORECASE)
                    if m:
                        datos["no_venta"] = m.group(1).strip()
                        break

        return datos
