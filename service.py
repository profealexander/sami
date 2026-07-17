"""
service.py — Capa 2: Servicio (Logica de negocio).

Orquesta: recibe imagen → guarda (via storage provider) → OCR (via ocr engine) → BD.
NO contiene logica directa de OCR ni de almacenamiento.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from config.logger import get_logger
from database import Comprobante
from ocr import get_ocr_engine
from storage import get_storage_backend
from utils.exceptions import OCRError

logger = get_logger("service")


@dataclass
class ComprobanteResponse:
    """Representación de la respuesta API, separada del modelo ORM."""

    registro: Comprobante
    transfiere: str | None
    no_comprobante: str | None
    monto: str | None
    ocr_exitoso: bool
    ocr: str | None



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
            "OCR exitoso — proveedor=%s | transfiere=%s | no_comprobante=%s | monto=%s",
            engine.nombre,
            resultado.transfiere or "N/A",
            resultado.no_comprobante or "N/A",
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

    # ── Extraer campos del OCR (None si el OCR falló por completo) ──
    if resultado is not None:
        data_orm = resultado.model_dump(exclude_none=True)
    else:
        data_orm = {}

    # ── Guardar en BD (model_dump propaga automáticamente los campos comunes) ──
    nuevo_comprobante = Comprobante(
        **data_orm,
        cliente_id=cliente_id,
        ruta_imagen=ruta_imagen,
    )

    db.add(nuevo_comprobante)
    db.commit()
    db.refresh(nuevo_comprobante)

    tiene_campos = any([data_orm.get(k) for k in ("transfiere", "monto", "no_comprobante")])
    logger.info(
        "Comprobante #%s registrado | cliente=%s | OCR=%s | transfiere=%s | no_comprobante=%s",
        nuevo_comprobante.id,
        cliente_id,
        engine.nombre,
        data_orm.get("transfiere", "N/A"),
        data_orm.get("no_comprobante", "N/A"),
    )

    return ComprobanteResponse(
        registro=nuevo_comprobante,
        transfiere=data_orm.get("transfiere"),
        no_comprobante=data_orm.get("no_comprobante"),
        monto=data_orm.get("monto"),
        ocr_exitoso=resultado is not None and tiene_campos,
        ocr=resultado.ocr if resultado and tiene_campos else None,
    )


def _resolver_ruta_imagen(ruta_imagen: str, backend) -> str:
    """Resuelve ruta de BD a ruta accesible para OCR usando el backend."""
    return backend.resolver_ruta(ruta_imagen)


def _limpiar_temporal(ruta_absoluta: str, _ruta_original: str, backend) -> None:
    """Elimina archivo temporal usando el backend."""
    backend.limpiar_temporal(ruta_absoluta)
