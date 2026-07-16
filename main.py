"""
main.py — Capa 1: Controlador FastAPI.

Rutas, CORS, validacion de uploads y montaje de estaticos.
Delega la logica de negocio a service.py.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db
import service
from config.logger import get_logger
from config.server import server_config
from config.settings import settings
from utils.exceptions import UploadValidationError, OCRError, StorageError
from utils.upload_validator import (
    configure as configure_validator,
    validar_archivo,
    validar_cliente_id,
    sanitizar_filename,
)
from utils.auth import validar_api_key
from utils.rate_limiter import RateLimiter

logger = get_logger("api")

# ── Rate limiter global ──
# NOTA: usa server_config.rate_limit (antes hardcodeado a 10/60 e ignoraba
# la variable RATE_LIMIT del .env). Sigue siendo in-memory por proceso:
# con WORKERS=1 esto es correcto; si algun dia se sube WORKERS>1, cada
# proceso tendria su propio contador y el limite efectivo se multiplicaria
# por el numero de workers — revisar si eso llega a pasar.
_rate_limiter = RateLimiter(max_requests=server_config.rate_limit, window_seconds=60)

# ── Executor dedicado para trabajo I/O-bound (llamadas a OCR.space, etc.) ──
# Tamano derivado de IO_POOL_SIZE (config/server.py), que a su vez se
# calcula a partir de os.cpu_count() y es sobreescribible por .env.
# Reemplaza al executor por defecto de asyncio (run_in_executor(None, ...))
# para tener control explicito sobre cuantos uploads se procesan en
# paralelo dentro de este proceso.
_io_executor = ThreadPoolExecutor(
    max_workers=server_config.io_pool_size,
    thread_name_prefix="upload",
)

# ── Configurar validador de uploads ──
configure_validator(
    max_size_mb=settings.max_upload_size_mb,
    allowed_extensions=settings.allowed_extensions,
)

app = FastAPI(title="SAMI - Servidor de Comprobantes OCR")

# Validar CORS en producción
if server_config.env == "production" and server_config.cors_origins == ["*"]:
    logger.warning("CORS * configurado en producción — riesgo de seguridad. Configurar CORS_ORIGINS explícito.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware CSP (Content Security Policy)
@app.middleware("http")
async def csp_middleware(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_event():
    """Inicializar tablas de BD al arrancar el servidor."""
    from database.engine import engine
    from database.models import Base
    Base.metadata.create_all(bind=engine)
    logger.info(
        "Base de datos inicializada correctamente | workers=%d | io_pool_size=%d",
        server_config.workers, server_config.io_pool_size,
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cierra el executor de I/O de forma ordenada al apagar el servidor."""
    _io_executor.shutdown(wait=True)
    logger.info("Executor de I/O cerrado correctamente")


@app.get("/health", description="Verifica que el servidor esta vivo y funcionando correctamente")
def health_check():
    """Health check. Retorna estado, version, entorno y estado de BD."""
    from sqlalchemy import text
    from importlib.metadata import version as get_version

    try:
        app_version = get_version("sami")
    except Exception:
        app_version = "unknown"

    status = {
        "status": "ok",
        "version": app_version,
        "entorno": server_config.env,
        "workers": server_config.workers,
        "io_pool_size": server_config.io_pool_size,
    }
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        status["database"] = "ok"
    except Exception as e:
        status["status"] = "degraded"
        status["database"] = f"error: {type(e).__name__}"
    return status


@app.get("/", description="Sirve el frontend PWA para captura de comprobantes desde el movil")
def leer_index():
    """Sirve el frontend PWA (static/index.html) para uso desde el movil."""
    return FileResponse("static/index.html")


@app.post("/api/upload", description="Sube una foto de comprobante y extrae su texto mediante OCR")
async def subir_comprobante(
    request: Request,
    imagen: UploadFile = File(..., description="Imagen del comprobante en formato JPG, PNG o WebP"),
    cliente_id: str = Form(..., description="Identificador unico del cliente, tienda o cajero (ej: 'tienda_001')"),
    db: Session = Depends(get_db),
    x_api_key: str = Header(default=""),
):
    """Endpoint principal de captura de comprobantes.

    Recibe una imagen, la valida, pasa por OCR multi-proveedor,
    guarda los datos extraidos en base de datos y retorna
    la informacion del comprobante procesado.

    El proveedor OCR se configura via variable OCR_PROVIDER en .env
    (gemini, tesseract u ocrspace). Si falla, cae automaticamente
    a Tesseract como fallback local.
    """
    # Rate limiting
    # NOTA: por IP. Si varios cajeros comparten la misma red/IP de tienda,
    # este limite los agrupa como un solo cliente — considerar migrar a
    # limitar por cliente_id si eso empieza a causar falsos positivos.
    client_ip = request.client.host if request and request.client else "unknown"
    if not _rate_limiter.permitir(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit excedido. Intente mas tarde.")

    # Autenticación (solo en producción)
    if server_config.env == "production" and not validar_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="API key inválida")

    cliente_id = cliente_id.strip()
    if not cliente_id:
        raise HTTPException(
            status_code=422,
            detail="cliente_id es requerido y no puede estar vacio",
        )
    validar_cliente_id(cliente_id)

    try:
        # Streaming: escribir chunks a disco en lugar de cargar todo a RAM
        CHUNK_SIZE = 8192
        nombre_seguro = sanitizar_filename(imagen.filename or "captura.jpg")
        ext = f".{nombre_seguro.rsplit('.', 1)[-1]}" if "." in nombre_seguro else ".jpg"

        # Guardar directamente a disco con streaming
        import tempfile
        from pathlib import Path
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir="uploads")
        total_bytes = 0
        while True:
            chunk = await imagen.read(CHUNK_SIZE)
            if not chunk:
                break
            tmp.write(chunk)
            total_bytes += len(chunk)
        tmp.close()

        safe_filename = (imagen.filename or "unknown").replace("\n", "").replace("\r", "")
        logger.info(
            "Upload recibido — filename=%s | size=%d KB | cliente=%s",
            safe_filename,
            total_bytes // 1024,
            cliente_id,
        )

        # Validar desde el archivo en disco
        with open(tmp.name, "rb") as f:
            contenido = f.read()
        validar_archivo(contenido, imagen.filename or "captura.jpg")
        contenido = None  # Liberar memoria

        # Mover a nombre final con UUID
        import uuid
        ruta_final = Path("uploads") / f"{uuid.uuid4().hex}{ext}"
        Path(tmp.name).rename(ruta_final)
        ruta_imagen = str(ruta_final)

        respuesta = await asyncio.get_running_loop().run_in_executor(
            _io_executor, service.procesar_y_guardar_comprobante, db, ruta_imagen, cliente_id
        )

        registro = respuesta.registro
        logger.info(
            "Upload exitoso — id=%s | cliente=%s | cajero=%s",
            registro.id, cliente_id, registro.cajero,
        )

        response_data = {
            "status": "success",
            "mensaje": "Comprobante procesado y guardado",
            "ocr_exitoso": respuesta.ocr_exitoso,
            "proveedor_ocr": respuesta.proveedor_ocr,
            "datos_extraidos": {
                "cajero": registro.cajero,
                "fecha": registro.fecha_comprobante,
                "hora": registro.hora_comprobante,
                "venta_no": registro.no_venta,
            },
        }

        # Incluir campos extendidos del OCR
        if respuesta.monto is not None:
            response_data["datos_extraidos"]["monto"] = respuesta.monto
        if respuesta.destinatario is not None:
            response_data["datos_extraidos"]["destinatario"] = respuesta.destinatario

        return response_data

    except UploadValidationError as e:
        logger.warning("Upload rechazado: %s", e.mensaje)
        raise HTTPException(status_code=e.codigo, detail=e.causa or e.mensaje)

    except OCRError as e:
        logger.error("Error OCR en upload: %s", e.mensaje)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando OCR con {e.proveedor}: {e.causa}",
        )

    except StorageError as e:
        logger.error("Error de almacenamiento: %s", e.mensaje)
        raise HTTPException(
            status_code=500,
            detail=f"Error guardando imagen en {e.backend}: {e.causa}",
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Error inesperado en /api/upload")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor",
        )


@app.exception_handler(Exception)
async def error_global(request: Request, exc: Exception):
    """Captura cualquier excepcion no manejada y retorna 500."""
    logger.exception("Excepcion no capturada en %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )
