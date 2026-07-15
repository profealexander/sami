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
    validar_cliente_id,
    sanitizar_filename,
)

logger = get_logger("api")

# ── Configurar validador de uploads ──
configure_validator(
    max_size_mb=settings.max_upload_size_mb,
    allowed_extensions=settings.allowed_extensions,
)

app = FastAPI(title="SAMI - Servidor de Comprobantes OCR")


app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health", description="Verifica que el servidor esta vivo y funcionando correctamente")
def health_check():
    """Health check. Retorna estado, version y entorno activo."""
    return {"status": "ok", "version": "2.2.0", "entorno": server_config.env}


@app.get("/", description="Sirve el frontend PWA para captura de comprobantes desde el movil")
def leer_index():
    """Sirve el frontend PWA (static/index.html) para uso desde el movil."""
    return FileResponse("static/index.html")


@app.post("/api/upload", description="Sube una foto de comprobante y extrae su texto mediante OCR")
async def subir_comprobante(
    imagen: UploadFile = File(..., description="Imagen del comprobante en formato JPG, PNG o WebP"),
    cliente_id: str = Form(..., description="Identificador unico del cliente, tienda o cajero (ej: 'tienda_001')"),
    db: Session = Depends(get_db),
):
    """Endpoint principal de captura de comprobantes.

    Recibe una imagen, la valida, pasa por OCR multi-proveedor,
    guarda los datos extraidos en base de datos y retorna
    la informacion del comprobante procesado.

    El proveedor OCR se configura via variable OCR_PROVIDER en .env
    (gemini, tesseract u ocrspace). Si falla, cae automaticamente
    a Tesseract como fallback local.
    """
    cliente_id = cliente_id.strip()
    if not cliente_id:
        raise HTTPException(
            status_code=422,
            detail="cliente_id es requerido y no puede estar vacio",
        )
    validar_cliente_id(cliente_id)

    try:
        contenido = await imagen.read()
        logger.info(
            "Upload recibido — filename=%s | size=%d KB | cliente=%s",
            imagen.filename,
            len(contenido) // 1024,
            cliente_id,
        )
        validar_archivo(contenido, imagen.filename or "captura.jpg")

        nombre_seguro = sanitizar_filename(imagen.filename or "captura.jpg")
        ext = f".{nombre_seguro.rsplit('.', 1)[-1]}" if "." in nombre_seguro else ".jpg"

        ruta_imagen = service.guardar_imagen_fisica(contenido, ext)
        registro = service.procesar_y_guardar_comprobante(db, ruta_imagen, cliente_id)

        logger.info(
            "Upload exitoso — id=%s | cliente=%s | cajero=%s",
            registro.id, cliente_id, registro.cajero,
        )

        response_data = {
            "status": "success",
            "mensaje": "Comprobante procesado y guardado",
            "datos_extraidos": {
                "cajero": registro.cajero,
                "fecha": registro.fecha_comprobante,
                "hora": registro.hora_comprobante,
                "venta_no": registro.no_venta,
            },
        }

        # Incluir campos extendidos si existen
        monto = getattr(registro, "_monto", None)
        destinatario = getattr(registro, "_destinatario", None)
        if monto:
            response_data["datos_extraidos"]["monto"] = monto
        if destinatario:
            response_data["datos_extraidos"]["destinatario"] = destinatario

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
            detail=f"Error interno del servidor: {str(e)[:200]}",
        )


@app.exception_handler(Exception)
async def error_global(request: Request, exc: Exception):
    """Captura cualquier excepcion no manejada y retorna 500."""
    logger.exception("Excepcion no capturada en %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )
