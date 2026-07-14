"""
tesseract_provider.py — Proveedor OCR usando Tesseract local.

Configuración auto-contenida en TesseractConfig.
Parámetros editables desde .env sin tocar código.

Patrones de extracción soportados:
  - Tickets/venta:  CAJERO, VENDEDOR, VENTA, TICKET, FACTURA
  - Transferencias: $ monto, De (remitente), A (destinatario), fecha textual
  - Fechas:         DD/MM/AAAA, DD-MM-AAAA, "El DD de mes de AAAA"
  - Horas:          HH:MM
"""

import os
import re
from dataclasses import dataclass

import pytesseract
from PIL import Image, ImageFilter

from ocr.base import OCRProvider, OCRResult

# ── Meses en español para parseo de fechas textuales ──
MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# ── Errores OCR comunes en meses (Tesseract a veces lee mal) ──
MESES_FALLBACK = {
    "jullo": "julio", "junlo": "junio", "julio": "julio",
    "enero": "enero", "febrero": "febrero", "marzo": "marzo",
    "abril": "abril", "mayo": "mayo", "agosto": "agosto",
    "setiembre": "septiembre", "octubre": "octubre",
    "noviembre": "noviembre", "diziembre": "diciembre",
}

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
        """Crea el provider desde variables de entorno y .env."""
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
        """Nombre del proveedor: tesseract."""
        return "tesseract"

    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        """Procesa la imagen con Tesseract OCR y retorna los campos extraidos."""
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
            monto=campos.get("monto"),
            destinatario=campos.get("destinatario"),
            texto_completo=texto_completo.strip(),
            proveedor=self.nombre,
        )

    def _preprocesar(self, img: Image.Image) -> Image.Image:
        """Preprocesa la imagen para mejorar la precisión de Tesseract."""
        if self.config.scale != 1.0:
            w, h = img.size
            img = img.resize(
                (int(w * self.config.scale), int(h * self.config.scale)),
                Image.LANCZOS,
            )
        img = img.convert("L")
        if self.config.denoise:
            img = img.filter(ImageFilter.MedianFilter(3))
        if self.config.threshold == 0:
            pixeles = list(img.getdata())
            umbral = sum(pixeles) // len(pixeles)
            img = img.point(lambda p: 255 if p > umbral else 0)
        elif self.config.threshold < 255:
            img = img.point(lambda p: 255 if p > self.config.threshold else 0)
        return img

    def _parsear_campos(self, texto: str) -> dict:
        """Extrae campos estructurados del texto OCR.

        Soporta tickets de venta y transferencias bancarias.
        """
        datos = {
            "cajero": None, "fecha": None, "hora": None,
            "no_venta": None, "monto": None, "destinatario": None,
        }

        for linea in texto.split("\n"):
            linea = linea.strip()
            if not linea:
                continue

            # ── Cajero (tickets) ──
            m = re.search(
                r'(?:CAJERO|ATENDIO|ATENDIÓ|CAJER@|VENDEDOR)\s*[\:\-]?\s*(.+)',
                linea, re.IGNORECASE,
            )
            if m and not datos["cajero"]:
                datos["cajero"] = m.group(1).strip()

            # ── Remitente (transferencias: "De Juan Perez") ──
            m = re.search(r'^De\s+(.+)$', linea, re.IGNORECASE)
            if m and not datos["cajero"]:
                datos["cajero"] = m.group(1).strip()

            # ── Destinatario (transferencias: "A Maria Lopez") ──
            m = re.search(r'^A\s+(.+)$', linea, re.IGNORECASE)
            if m and not datos["destinatario"]:
                datos["destinatario"] = m.group(1).strip()

            # ── Monto ($ XX.XX) ──
            m = re.search(r'\$\s*([0-9]+[\.\,]?[0-9]*)', linea)
            if m and not datos["monto"]:
                datos["monto"] = m.group(1)

            # ── Fecha numérica ──
            m = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})', linea)
            if m and not datos["fecha"]:
                d, mes, a = m.group(1), m.group(2), m.group(3)
                if 1 <= int(d) <= 31 and 1 <= int(mes) <= 12:
                    datos["fecha"] = f"{int(d):02d}/{int(mes):02d}/{a}"

            # ── Fecha textual: "El 06 de julio de 2026" ──
            m = re.search(
                r'El\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})',
                linea, re.IGNORECASE,
            )
            if m and not datos["fecha"]:
                dia, mes_str, anio = m.group(1), m.group(2).lower(), m.group(3)
                mes_num = MESES_ES.get(mes_str) or MESES_ES.get(MESES_FALLBACK.get(mes_str, ""))
                if mes_num:
                    datos["fecha"] = f"{int(dia):02d}/{mes_num:02d}/{anio}"

            # ── Hora ──
            m = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', linea)
            if m and not datos["hora"]:
                h, mi = int(m.group(1)), int(m.group(2))
                if 0 <= h <= 23 and 0 <= mi <= 59:
                    datos["hora"] = f"{h:02d}:{mi:02d}"

            # ── Número de comprobante ──
            if not datos["no_venta"]:
                for pat in [
                    r'(?:VENTA|TICKET|FACTURA|COMPROBANTE)\s*[\:\-]?\s*(\d[\d\-/]*)',
                    r'(?:No\.?|N°|NUMERO)\s*[\:\-]?\s*(\d[\d\-]*)',
                    r'N[°\*]\s*de\s+(?:comprobante|venta|ticket)\s*[\:\-]?\s*(\d[\d\-]*)',
                ]:
                    m = re.search(pat, linea, re.IGNORECASE)
                    if m:
                        datos["no_venta"] = m.group(1).strip()
                        break

        return datos
