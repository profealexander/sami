"""
service.py — Capa 2: Servicio (Logica de negocio).

Orquesta: recibe imagen → guarda (via storage provider) → OCR (via ocr engine) → BD.
NO contiene logica directa de OCR ni de almacenamiento.
"""

import os
import tempfile
import uuid
from datetime import datetime

import requests

from sqlalchemy.orm import Session

from config.logger import get_logger
from config.server import server_config
from config.settings import PROJECT_ROOT
from database import Comprobante
from ocr import get_ocr_engine
from storage import get_storage_backend
from utils.exceptions import OCRError

logger = get_logger("service")


def guardar_imagen_fisica(imagen_bytes: bytes, extension: str) -> str:
    """Guarda imagen en disco segun backend configurado (local/s3/cloudinary) y retorna ruta."""
    nombre_archivo = f"{uuid.uuid4().hex}{extension}"
    backend = get_storage_backend()
    ruta = backend.guardar(imagen_bytes, nombre_archivo)
    logger.info("Imagen guardada: %s (backend=%s)", ruta, backend.nombre)
    return ruta


def procesar_y_guardar_comprobante(
    db: Session,
    ruta_imagen: str,
    cliente_id: str,
) -> Comprobante:
    """
    Procesa una imagen: OCR + guardado en BD.

    Args:
        db: Sesion de BD
        ruta_imagen: Ruta relativa (local) o URL (S3/Cloudinary)
        cliente_id: Identificador del cliente

    Returns:
        Comprobante registrado en BD
    """
    engine = get_ocr_engine()
    ruta_absoluta = _resolver_ruta_imagen(ruta_imagen)

    # ── Ejecutar OCR ──
    try:
        resultado = engine.extraer_campos(ruta_absoluta)
        logger.info(
            "OCR exitoso — proveedor=%s | cajero=%s | fecha=%s | monto=%s",
            engine.nombre,
            resultado.cajero or "N/A",
            resultado.fecha or "N/A",
            resultado.monto or "N/A",
        )
    except OCRError:
        raise
    except Exception as e:
        logger.error(
            "Error OCR en %s — tipo=%s | msg=%s",
            ruta_imagen,
            type(e).__name__,
            str(e)[:300],
        )
        resultado = None

    _limpiar_temporal(ruta_absoluta, ruta_imagen)

    # ── Valores por defecto si OCR falló ──
    cajero = resultado.cajero if resultado and resultado.cajero else "OCR no disponible"
    fecha = resultado.fecha if resultado and resultado.fecha else "OCR no disponible"
    hora = resultado.hora if resultado and resultado.hora else "OCR no disponible"
    no_venta = resultado.no_venta if resultado and resultado.no_venta else None

    # ── Guardar en BD ──
    nuevo_comprobante = Comprobante(
        cajero=cajero,
        fecha_comprobante=fecha,
        hora_comprobante=hora,
        no_venta=no_venta,
        cliente_id=cliente_id,
        fecha_envio=datetime.now(),
        ruta_imagen=ruta_imagen,
    )

    db.add(nuevo_comprobante)
    db.commit()
    db.refresh(nuevo_comprobante)

    logger.info(
        "Comprobante #%s registrado | cliente=%s | OCR=%s | cajero=%s | fecha=%s",
        nuevo_comprobante.id,
        cliente_id,
        engine.nombre,
        cajero,
        fecha,
    )

    # Adjuntar campos extendidos al objeto para que la API los devuelva
    if resultado:
        nuevo_comprobante._monto = resultado.monto
        nuevo_comprobante._destinatario = resultado.destinatario
    else:
        nuevo_comprobante._monto = None
        nuevo_comprobante._destinatario = None

    return nuevo_comprobante


def _resolver_ruta_imagen(ruta_imagen: str) -> str:
    """Convierte ruta relativa en BD a ruta absoluta del archivo fisico."""
    if server_config.storage_backend == "local":
        return str(PROJECT_ROOT / ruta_imagen)

    logger.info("Descargando imagen remota: %s", ruta_imagen)
    resp = requests.get(ruta_imagen, timeout=30)
    resp.raise_for_status()

    ext = ruta_imagen.split(".")[-1].split("?")[0] if "." in ruta_imagen else "jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
    tmp.write(resp.content)
    tmp.close()
    return tmp.name


def _limpiar_temporal(ruta_absoluta: str, ruta_original: str) -> None:
    """Elimina archivo temporal y la copia original del storage."""
    if server_config.storage_backend != "local" and os.path.exists(ruta_absoluta):
        os.remove(ruta_absoluta)
        logger.debug("Temporal eliminado: %s", ruta_absoluta)
