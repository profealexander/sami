"""
tesseract_provider.py — Proveedor OCR usando Tesseract local.

Configuración auto-contenida en TesseractConfig.
Parámetros editables desde .env sin tocar código.

Patrones de extracción soportados:
  - Tickets/venta:  CAJERO, VENDEDOR, VENTA, TICKET, FACTURA
  - Transferencias: $ monto, De (remitente), A (destinatario), fecha textual
  - Fechas:         DD/MM/AAAA, DD-MM-AAAA, "El DD de mes de AAAA"
  - Horas:          HH:MM

NOTA SOBRE CONCURRENCIA:
Tesseract es CPU-bound. TESSERACT_MAX_CONCURRENT limita cuántas
instancias corren en paralelo DENTRO de este proceso, para no saturar
los cores disponibles cuando varias imágenes caen a fallback al mismo
tiempo. El default se deriva de cpu_count // workers (workers viene de
server_config), para que la suma de instancias concurrentes entre TODOS
los procesos Uvicorn nunca exceda los cores físicos del VPS. Es
sobreescribible manualmente vía .env si se necesita otro valor.
"""

import os
import threading
from dataclasses import dataclass

import pytesseract
from PIL import Image, ImageFilter

from ocr.base import OCRProvider, OCRResult
from ocr.parsers import parsear_campos

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
    threshold: int = 0  # 0 = Otsu automático
    denoise: bool = True
    psm: int = 3
    max_concurrent: int = 1

    @classmethod
    def from_env(cls) -> "TesseractConfig":
        """Crea el provider desde variables de entorno y .env.

        max_concurrent por defecto = cpu_count // workers (mínimo 1), para
        que la concurrencia total de Tesseract entre todos los procesos
        Uvicorn no exceda los cores físicos disponibles.
        """
        from config import settings

        cpu_count = os.cpu_count() or 1
        workers = max(1, getattr(settings, "workers", 1))
        concurrent_default = max(1, cpu_count // workers)

        cfg = cls(
            cmd=os.getenv("TESSERACT_CMD", "").strip(),
            lang=os.getenv("TESSERACT_LANG", "spa").strip(),
            scale=float(os.getenv("TESSERACT_SCALE", "2.0")),
            threshold=int(os.getenv("TESSERACT_THRESHOLD", "0")),
            denoise=os.getenv("TESSERACT_DENOISE", "true").lower() == "true",
            psm=int(os.getenv("TESSERACT_PSM", "3")),
            max_concurrent=int(
                os.getenv("TESSERACT_MAX_CONCURRENT", str(concurrent_default))
            ),
        )
        # Auto-detectar ruta si no se especificó
        if not cfg.cmd or not os.path.exists(cfg.cmd):
            for ruta in RUTAS_POR_DEFECTO:
                if os.path.exists(ruta):
                    cfg.cmd = ruta
                    break
        return cfg


# ── Semáforo singleton a nivel de módulo ──
# Compartido entre instancias de TesseractProvider dentro del mismo proceso
# (mismo patrón que _gemini_client / _s3_client en los otros providers).
_tesseract_semaphore: threading.Semaphore | None = None
_tesseract_semaphore_size: int | None = None


def _get_tesseract_semaphore(max_concurrent: int) -> threading.Semaphore:
    """Devuelve el semáforo compartido, recreándolo solo si cambia el tamaño."""
    global _tesseract_semaphore, _tesseract_semaphore_size
    if _tesseract_semaphore is None or _tesseract_semaphore_size != max_concurrent:
        _tesseract_semaphore = threading.Semaphore(max_concurrent)
        _tesseract_semaphore_size = max_concurrent
    return _tesseract_semaphore


class TesseractProvider(OCRProvider):
    """OCR mediante Tesseract con preprocesamiento de imagen."""

    def __init__(self):
        self.config = TesseractConfig.from_env()
        self._semaphore = _get_tesseract_semaphore(self.config.max_concurrent)
        self._cache = None
        if self.config.cmd and os.path.exists(self.config.cmd):
            pytesseract.pytesseract.tesseract_cmd = self.config.cmd

    @property
    def nombre(self) -> str:
        """Nombre del proveedor: tesseract."""
        return "tesseract"

    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        """Procesa la imagen con Tesseract OCR y retorna los campos extraidos.

        Limitado por semáforo (TESSERACT_MAX_CONCURRENT) para no saturar
        los cores del VPS cuando varias imágenes caen a fallback a la vez.
        Incluye cache simple de preprocesamiento por hash de imagen + config.
        """
        if not self.config.cmd or not os.path.exists(self.config.cmd):
            return OCRResult(texto_completo="", proveedor=self.nombre)

        with self._semaphore:
            import hashlib

            img = Image.open(ruta_imagen)

            # Cache simple: hash de la imagen + config
            cache_key = hashlib.md5(img.tobytes()).hexdigest()
            cache_key += (
                f":{self.config.scale}:{self.config.threshold}:{self.config.denoise}"
            )

            if self._cache is None or self._cache.get("key") != cache_key:
                img_preprocesada = self._preprocesar(img)
                self._cache = {"key": cache_key, "img": img_preprocesada}
            else:
                img_preprocesada = self._cache["img"]

            config_str = f"--psm {self.config.psm}"
            texto_completo = pytesseract.image_to_string(
                img_preprocesada, lang=self.config.lang, config=config_str
            )

        campos = parsear_campos(texto_completo)

        return OCRResult(
            transfiere=campos.get("transfiere"),
            no_comprobante=campos.get("no_comprobante"),
            monto=campos.get("monto"),
            texto_completo=texto_completo.strip(),
            proveedor=self.nombre,
        )

    def _preprocesar(self, img: Image.Image) -> Image.Image:
        """Preprocesa la imagen para mejorar la precisión de Tesseract."""
        if self.config.scale != 1.0:
            w, h = img.size
            img = img.resize(
                (int(w * self.config.scale), int(h * self.config.scale)),
                Image.Resampling.LANCZOS,
            )
        img = img.convert("L")
        if self.config.denoise:
            img = img.filter(ImageFilter.MedianFilter(3))
        if self.config.threshold == 0:
            # Usar histogram() en lugar de list(getdata()) — 100x menos RAM
            hist = img.histogram()
            total = sum(i * c for i, c in enumerate(hist))
            count = sum(hist)
            umbral = total // count if count > 0 else 128
            img = img.point(lambda p: 255 if p > umbral else 0)
        elif self.config.threshold < 255:
            img = img.point(lambda p: 255 if p > self.config.threshold else 0)
        return img
