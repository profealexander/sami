"""
main.py — Capa 1: Controlador FastAPI.

Rutas, CORS, validacion de uploads y montaje de estaticos.
Delega la logica de negocio a service.py.
"""

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
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
    sanitizar_filename,
    validar_tamano,
)

logger = get_logger("api")

# ── Configurar validador de uploads ──
configure_validator(
    max_size_mb=settings.max_upload_size_mb,
    allowed_extensions=settings.allowed_extensions,
)

app = FastAPI(title="SAMI - Servidor de Comprobantes OCR")


# ── CORS configurable ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Montar carpeta estatica ──
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Health check ──
@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.1.0", "entorno": server_config.env}


# ── Ruta raiz (PWA) ──
@app.get("/")
def leer_index():
    return FileResponse("static/index.html")


# ── Endpoint principal ──
@app.post("/api/upload")
async def subir_comprobante(
    imagen: UploadFile = File(...),
    cliente_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Sube una imagen de comprobante, ejecuta OCR y guarda en BD.

    Validaciones:
        - Tamaño maximo: configurable via MAX_UPLOAD_SIZE_MB (default 10 MB)
        - Extensiones permitidas: .jpg, .jpeg, .png, .webp
        - Tipo MIME real verificado por magic bytes
    """
    cliente_id = cliente_id.strip()
    if not cliente_id:
        raise HTTPException(
            status_code=422,
            detail="cliente_id es requerido y no puede estar vacio",
        )

    try:
        # 1. Leer contenido
        contenido = await imagen.read()

        # 2. Validar tamaño, extensión y tipo real
        logger.info(
            "Upload recibido — filename=%s | size=%d KB | cliente=%s",
            imagen.filename,
            len(contenido) // 1024,
            cliente_id,
        )
        validar_archivo(contenido, imagen.filename or "captura.jpg")

        # 3. Sanitizar y determinar extension
        nombre_seguro = sanitizar_filename(imagen.filename or "captura.jpg")
        ext = f".{nombre_seguro.rsplit('.', 1)[-1]}" if "." in nombre_seguro else ".jpg"

        # 4. Guardar fisicamente y procesar OCR
        ruta_imagen = service.guardar_imagen_fisica(contenido, ext)
        registro = service.procesar_y_guardar_comprobante(db, ruta_imagen, cliente_id)

        logger.info(
            "Upload exitoso — id=%s | cliente=%s | cajero=%s",
            registro.id, cliente_id, registro.cajero,
        )

        return {
            "status": "success",
            "mensaje": "Comprobante procesado y guardado",
            "datos_extraidos": {
                "cajero": registro.cajero,
                "fecha": registro.fecha_comprobante,
                "hora": registro.hora_comprobante,
                "venta_no": registro.no_venta,
            },
        }

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
        # Relanzar excepciones HTTP que ya construimos
        raise

    except Exception as e:
        logger.exception("Error inesperado en /api/upload")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)[:200]}",
        )


# ── Manejador global de errores no capturados ──
@app.exception_handler(Exception)
async def error_global(request: Request, exc: Exception):
    logger.exception("Excepcion no capturada en %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )
