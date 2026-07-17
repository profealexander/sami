# SAMI — Sistema de Archivo y Manejo de Imágenes de Comprobantes

> Captura de comprobantes desde el teléfono, OCR multi-proveedor con fallback automático y almacenamiento flexible (local/S3/Cloudinary).
> **v2.0.0** — Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic Settings

---

## Arquitectura (3 capas + estrategias + utilidades)

```
run.py → boots uvicorn con main:app
 ├─ main.py              Capa 1 (controlador): rutas FastAPI, CORS, CSP, upload streaming, PWA
 ├─ service.py           Capa 2 (negocio): orquesta OCR + almacenamiento + BD
 ├─ database/            Capa 3 (repositorio): SQLAlchemy ORM, SQLite + PostgreSQL
 │   └─ backends/        sqlite.py, postgres.py (añadir nuevos aquí)
 ├─ ocr/                 Estrategia OCR: 3 proveedores + fallback + circuit breaker
 ├─ storage/             Estrategia almacenamiento: local, S3, Cloudinary
 ├─ config/              Config unificada con pydantic-settings + logging rotativo
 └─ utils/               Auth, rate limiting, validación de uploads, excepciones
```

### Diagrama de flujo de datos

```
Cliente (móvil/PWA)
  → POST /api/upload (imagen + cliente_id)
    → main.py: validación (tamaño, tipo, extensión, cliente_id)
    → main.py: rate limiting (por IP) + auth (API key en producción)
    → run_in_executor → service.procesar_y_guardar_comprobante()
      → storage backend: guardar imagen (local | S3 | Cloudinary)
      → OCR engine: extraer_campos (Gemini | OCR.space | Tesseract + fallback)
      → ORM: Comprobante → base de datos (SQLite | PostgreSQL)
    → ComprobanteResponse → JSON al cliente
```

---

## Proveedores OCR

| Proveedor | Variable `.env` | Tipo | Límite gratis | Fallback automático |
|-----------|----------------|------|---------------|---------------------|
| Google Gemini | `OCR_PROVIDER=gemini` | API cloud (IA) | 1,500 req/día | → Tesseract |
| Tesseract | `OCR_PROVIDER=tesseract` | Local (sin internet) | Ilimitado | — |
| OCR.space | `OCR_PROVIDER=ocrspace` | API cloud | 25,000 req/mes | → Tesseract |

- **Fallback automático**: si el proveedor primario falla (red, cuota, timeout), cae a Tesseract local sin intervención
- **Circuit breaker**: tras 5 fallos consecutivos del primario, lo bloquea 60 segundos y usa solo el fallback
- **Compresión inteligente**: las imágenes >1MB o >4000px se redimensionan/recomprimen antes de enviar a APIs cloud
- **Cache de preprocesamiento**: Tesseract evita reprocesar imágenes idénticas (hash MD5)
- **Semáforo de concurrencia**: Tesseract limitado a `cpu_count // workers` instancias paralelas
- **Parsers compartidos**: todos los proveedores usan los mismos regex en `ocr/parsers.py` (cargados desde `ocr/patrones_ocr.toml`)

Cada proveedor tiene su propia configuración en `ocr/*_provider.py` con parámetros desde `.env` y `ocr/.env`.

---

## Backends de almacenamiento

| Backend | Variable `.env` | Descripción |
|---------|----------------|-------------|
| Local | `STORAGE_BACKEND=local` | Disco local (`uploads/`) |
| S3 | `STORAGE_BACKEND=s3` | Amazon S3 o compatible (Backblaze B2, MinIO) |
| Cloudinary | `STORAGE_BACKEND=cloudinary` | Cloudinary CDN |

Los backends remotos (S3, Cloudinary) descargan la imagen a un archivo temporal para OCR y lo limpian automáticamente al finalizar.

---

## Base de datos

| Motor | `DATABASE_URL` | Uso |
|-------|---------------|-----|
| SQLite | `sqlite:///./comprobantes.db` | Desarrollo, mono-usuario |
| PostgreSQL | `postgresql://user:pass@host:5432/sami` | Producción multi-worker |

- WAL mode + busy timeout en SQLite para escritura concurrente
- Pool de conexiones configurable en PostgreSQL
- Tablas creadas automáticamente en `startup` event (no requiere migraciones)

---

## Seguridad

| Característica | Implementación |
|---------------|----------------|
| Autenticación | API key vía header `X-Api-Key` (solo en producción) |
| Rate limiting | Configurable (default 100 req/min por IP) |
| CORS | Configurable vía `CORS_ORIGINS`, warning si `*` en producción |
| CSP Headers | `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` |
| Validación de uploads | Tamaño máximo, extensión permitida, magic bytes con Pillow |
| Sanitización de filenames | Elimina path traversal, caracteres peligrosos |
| Docker | USER no-root, HEALTHCHECK, `.dockerignore` completo |
| Secrets | Enmascarados en logs y `__repr__` |

---

## Entornos

| Entorno | Uso | Comando |
|---------|-----|---------|
| development | Local (PC, pendrive) | `python run.py` |
| production | VPS / Railway / Render / Docker | `ENV=production python run.py` |

Diferencias: producción usa más workers, sin reload, logs en nivel warning, CORS restringido, auth activo, host `0.0.0.0`.

---

## Variables de entorno (`.env`)

### Entorno y servidor
| Variable | Descripción | Default |
|----------|-------------|---------|
| `ENV` | development o production | development |
| `HOST` | IP del servidor | 127.0.0.1 (dev) / 0.0.0.0 (prod) |
| `PORT` | Puerto | 8000 |
| `WORKERS` | Workers | auto (1 dev / CPU count prod) |
| `IO_POOL_SIZE` | Hilos para uploads concurrentes | auto (min 32, CPU×8) |
| `RELOAD` | Hot-reload (solo dev) | auto |
| `LOG_LEVEL` | debug / info / warning / error | auto |
| `LOG_FILE` | Archivo de log (rotación diaria, 7 backups) | — |
| `CORS_ORIGINS` | Orígenes permitidos (`*` o lista) | `*` |
| `SAMI_API_KEY` | API key para autenticación (production) | — |
| `RATE_LIMIT` | Máximo de requests/minuto por IP | 100 |

### Base de datos
| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_URL` | `sqlite:///...` o `postgresql://...` | `sqlite:///./comprobantes.db` |
| `DB_POOL_SIZE` | Pool de conexiones PostgreSQL | 10 |

### Almacenamiento
| Variable | Descripción | Default |
|----------|-------------|---------|
| `STORAGE_BACKEND` | local / s3 / cloudinary | local |
| `UPLOAD_DIR` | Directorio de uploads (local) | uploads |
| `S3_BUCKET` | Bucket S3 | — |
| `S3_REGION` | Región AWS | — |
| `S3_ACCESS_KEY` | Access key S3 | — |
| `S3_SECRET_KEY` | Secret key S3 | — |
| `S3_ENDPOINT` | Endpoint S3 compatible (Backblaze B2, MinIO) | — |
| `CLOUDINARY_URL` | URL completa de Cloudinary | — |

### OCR (ver también `ocr/.env` y `ocr/.env.example`)
| Variable | Descripción | Default |
|----------|-------------|---------|
| `OCR_PROVIDER` | gemini / tesseract / ocrspace | ocrspace |
| `GEMINI_API_KEY` | API key de Google Gemini | — |
| `OCRSPACE_API_KEY` | API key de OCR.space | — |

Parámetros adicionales en `ocr/.env`: modelo Gemini, timeout, engine OCR.space, idioma Tesseract, escala, threshold, denoise, PSM, concurrencia máxima.

### Uploads
| Variable | Descripción | Default |
|----------|-------------|---------|
| `MAX_UPLOAD_SIZE_MB` | Tamaño máximo de imagen | 10 |
| `ALLOWED_EXTENSIONS` | Extensiones permitidas | .jpg,.jpeg,.png,.webp |

---

## Instalación

### Local
```bash
uv sync
python run.py
# http://localhost:8000
```

### Producción con PostgreSQL
```bash
docker compose up -d
```

### VPS / Railway / Render
```bash
ENV=production DATABASE_URL=postgresql://... python run.py
```

### Ngrok (acceso desde el móvil)
```bash
python run.py
ngrok http 8000
```

### GitHub → Render/Koyeb
Conectar repo, Render detecta `Procfile` automáticamente. Variables de entorno en el dashboard.

---

## Endpoints

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| GET | `/` | Frontend PWA (cámara + galería) | No |
| GET | `/health` | Health check (verifica BD, versión, workers) | No |
| GET | `/docs` | Documentación Swagger | No |
| POST | `/api/upload` | Sube imagen + cliente_id para OCR | Sí (production) |

**POST /api/upload** acepta:
- `imagen`: Archivo (JPEG, PNG, WebP) — hasta 10MB por defecto
- `cliente_id`: String (1-50 caracteres, alfanumérico + guiones y guión bajo)
- `X-Api-Key`: Header (solo en producción)

**Respuesta exitosa:**
```json
{
  "status": "success",
  "transfiere": "Juan Pérez",
  "no_comprobante": "0012481545",
  "monto": "150.00",
  "ocr_exitoso": true,
  "proveedor_ocr": "gemini"
}
```

---

## Testing

```bash
uv sync --all-extras
uv run pytest -v
```

6 archivos de test, 38 tests:

| Archivo | Tests | Descripción |
|---------|-------|-------------|
| `test_upload_validator.py` | 15 | Validación de tamaño, extensión, tipo real, cliente_id, sanitización |
| `test_parsers.py` | 9 | Parsers OCR: transfiere, no_comprobante, monto, texto_completo |
| `test_compresion.py` | 6 | Compresión de imágenes: umbrales, dimensiones, RGBA→RGB, aspect ratio |
| `test_config.py` | 6 | Configuración: importación, campos, tipos, entorno válido, cache singleton |
| `test_auth.py` | 4 | Autenticación API key: válida, inválida, vacía, sin configurar |
| `test_rate_limiter.py` | 4 | Rate limiting: permite, bloquea, independiente por IP |

Tests individuales:
```bash
uv run pytest tests/test_upload_validator.py::TestValidarClienteId::test_id_valido_tienda_001
```

---

## Frontend PWA

`static/index.html` es una PWA auto-contenida (sin build step):
- Tema oscuro, dos botones: cámara + galería
- Sube la imagen vía `fetch()` a `/api/upload` con `FormData`
- Muestra campos extraídos (`transfiere`, `no_comprobante`, `monto`)
- Genera un `cliente_id` aleatorio por sesión
- Service worker con estrategia network-first

---

## Docker

```bash
# Construir y arrancar
docker compose up -d

# Solo la app (con PostgreSQL externo)
docker build -t sami .
docker run -p 8000:8000 --env-file .env sami
```

El `docker-compose.yml` incluye:
- **sami**: app con healthcheck, volumenes para uploads y datos, restart unless-stopped
- **db**: PostgreSQL 16 Alpine con healthcheck, volumen persistente
- Variables de entorno cargadas desde `.env`

---

## Despliegue

### Procfile (Heroku / Render)
```
web: uv run python run.py
```

### Dockerfile
- `python:3.11-slim` con `tesseract-ocr` + `tesseract-ocr-spa`
- Usuario no-root (`sami`)
- HEALTHCHECK con `curl /health`
- `uv sync --frozen --no-dev`

---

## Cómo extender

### Nuevo proveedor OCR
1. Heredar `OCRProvider` de `ocr/base.py`
2. Implementar `nombre` (property) y `extraer_campos(ruta_imagen)` → `OCRResult`
3. Registrar con `registrar_ocr("nombre", MiProveedor)` en `ocr/__init__.py`

### Nuevo backend de almacenamiento
1. Heredar `StorageProvider` de `storage/base.py`
2. Implementar `nombre`, `guardar()`, opcionalmente `resolver_ruta()` y `limpiar_temporal()`
3. Registrar con `registrar_storage("nombre", MiBackend)` en `storage/__init__.py`

### Nuevo motor de base de datos
1. Crear `database/backends/new_engine.py` con función `create_*_engine(url, **kwargs)`
2. Registrar URL prefix en `database/engine.py::create_engine_from_url()`

---

## Deuda técnica conocida

Ver `BACKLOG.md` para lista completa. 3 items menores pendientes:
- `os.path.exists()` por request en Tesseract (~1ms overhead)
- Configuración PG incompleta (falta `max_overflow`, `pool_timeout`, `pool_recycle`)
- IO disco en cada log entry (mitigado con `TimedRotatingFileHandler`)
