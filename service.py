"""
service.py — Capa 2: Servicio (Logica de negocio).

Orquesta: recibe imagen → guarda (via storage provider) → OCR (via ocr engine) → BD.
NO contiene logica directa de OCR ni de almacenamiento.
"""

import os
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from database import Comprobante
from ocr import get_ocr_engine
from storage import get_storage_backend


def guardar_imagen_fisica(imagen_bytes: bytes, extension: str) -> str:
    """
    Guarda la imagen usando el backend configurado en STORAGE_BACKEND.
    Retorna ruta relativa (local) o URL publica (S3/Cloudinary).
    """
    nombre_archivo = f"{uuid.uuid4().hex}{extension}"
    backend = get_storage_backend()
    return backend.guardar(imagen_bytes, nombre_archivo)


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
    # 1. Obtener motor OCR (Gemini con fallback Tesseract)
    engine = get_ocr_engine()

    # 2. Resolver ruta absoluta si es local
    ruta_absoluta = _resolver_ruta_imagen(ruta_imagen)

    # 3. Ejecutar OCR
    try:
        resultado = engine.extraer_campos(ruta_absoluta)
    except Exception as e:
        print(f"[SAMI] Error OCR en {ruta_imagen}: {e}")
        resultado = None

    # 4. Limpiar temporal si se descargo de S3/Cloudinary
    _limpiar_temporal(ruta_absoluta, ruta_imagen)

    # 5. Valores por defecto si OCR fallo
    cajero = resultado.cajero if resultado and resultado.cajero else "OCR no disponible"
    fecha = resultado.fecha if resultado and resultado.fecha else "OCR no disponible"
    hora = resultado.hora if resultado and resultado.hora else "OCR no disponible"
    no_venta = resultado.no_venta if resultado and resultado.no_venta else None

    # 6. Guardar en BD
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

    print(f"[SAMI] Comprobante #{nuevo_comprobante.id} | "
          f"cliente={cliente_id} | OCR={engine.nombre} | "
          f"cajero={cajero} | fecha={fecha}")

    return nuevo_comprobante


def _resolver_ruta_imagen(ruta_imagen: str) -> str:
    """Convierte ruta relativa a absoluta, o descarga de S3/Cloudinary a temporal."""
    from config.server import server_config
    from config.settings import PROJECT_ROOT

    if server_config.storage_backend == "local":
        return str(PROJECT_ROOT / ruta_imagen)

    # Es URL de S3/Cloudinary → descargar a temporal
    import requests
    import tempfile

    resp = requests.get(ruta_imagen, timeout=30)
    resp.raise_for_status()

    ext = ruta_imagen.split(".")[-1].split("?")[0] if "." in ruta_imagen else "jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
    tmp.write(resp.content)
    tmp.close()
    return tmp.name


def _limpiar_temporal(ruta_absoluta: str, ruta_original: str) -> None:
    """Borra archivo temporal si la imagen vino de S3/Cloudinary."""
    from config.server import server_config

    if server_config.storage_backend != "local" and os.path.exists(ruta_absoluta):
        os.remove(ruta_absoluta)
