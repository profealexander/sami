from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db
import service
from config.server import server_config

app = FastAPI(title="SAMI - Servidor de Comprobantes OCR")

# ── CORS configurable (desarrollo: todo; produccion: origenes especificos) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar carpeta estatica para servir la PWA
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def leer_index():
    """Ruta raiz que carga la PWA"""
    return FileResponse("static/index.html")


@app.post("/api/upload")
async def subir_comprobante(
    imagen: UploadFile = File(...),
    cliente_id: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        contenido = await imagen.read()
        ext = f".{imagen.filename.split('.')[-1]}" if "." in imagen.filename else ".jpg"
        ruta_imagen = service.guardar_imagen_fisica(contenido, ext)
        registro = service.procesar_y_guardar_comprobante(db, ruta_imagen, cliente_id)

        return {
            "status": "success",
            "mensaje": "Comprobante procesado y guardado",
            "datos_extraidos": {
                "cajero": registro.cajero,
                "fecha": registro.fecha_comprobante,
                "hora": registro.hora_comprobante,
                "venta_no": registro.no_venta
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando imagen: {str(e)}")
