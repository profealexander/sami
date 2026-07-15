"""
service.py — Capa 2: Servicio (Logica de negocio).

Orquesta: recibe imagen → guarda (via storage provider) → OCR (via ocr engine) → BD.
NO contiene logica directa de OCR ni de almacenamiento.
"""

import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

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


@dataclass
class ComprobanteResponse:
    """Representación de la respuesta API, separada del modelo ORM."""
    registro: Comprobante
    monto: str | None
    destinatario: str | None
    ocr_exitoso: bool
    proveedor_ocr: str | None


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
) -> ComprobanteResponse:
    """
    Procesa una imagen: OCR + guardado en BD.

    Args:
        db: Sesion de BD
        ruta_imagen: Ruta relativa (local) o URL (S3/Cloudinary)
        cliente_id: Identificador del cliente

    Returns:
        ComprobanteResponse con registro y campos extendidos
    """
    engine = get_ocr_engine()
    backend = get_storage_backend()
    ruta_absoluta = None
    resultado = None

    # ── Ejecutar OCR con limpieza garantizada ──
    try:
        ruta_absoluta = _resolver_ruta_imagen(ruta_imagen, backend)
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
    finally:
        _limpiar_temporal(ruta_absoluta, ruta_imagen, backend)

    # ── Valores por defecto si OCR falló ──
    cajero = resultado.cajero if resultado and resultado.cajero else "OCR no disponible"
    fecha = resultado.fecha if resultado and resultado.fecha else "OCR no disponible"
    hora = resultado.hora if resultado and resultado.hora else "OCR no disponible"
    no_venta = resultado.no_venta if resultado and resultado.no_venta else None
    monto = resultado.monto if resultado else None
    destinatario = resultado.destinatario if resultado else None

    # ── Guardar en BD ──
    nuevo_comprobante = Comprobante(
        cajero=cajero,
        fecha_comprobante=fecha,
        hora_comprobante=hora,
        no_venta=no_venta,
        monto=monto,
        destinatario=destinatario,
        cliente_id=cliente_id,
        fecha_envio=datetime.now(timezone.utc),
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

    return ComprobanteResponse(
        registro=nuevo_comprobante,
        monto=monto,
        destinatario=destinatario,
        ocr_exitoso=resultado is not None,
        proveedor_ocr=engine.nombre if resultado else None,
    )


def _resolver_ruta_imagen(ruta_imagen: str, backend) -> str:
    """Resuelve ruta de BD a ruta accesible para OCR usando el backend."""
    return backend.resolver_ruta(ruta_imagen)


def _limpiar_temporal(ruta_absoluta: str, ruta_original: str, backend) -> None:
    """Elimina archivo temporal usando el backend."""
    backend.limpiar_temporal(ruta_absoluta)
