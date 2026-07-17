# BACKLOG — SAMI v2

Proximos pasos y funcionalidades pendientes.

---

## Completado (Fase 1 — 2026-07-14)

- ✅ **Bug 2**: `imghdr` deprecado reemplazado por `PIL.Image` en `upload_validator.py`
- ✅ **Bug 7**: Validación de `cliente_id` con regex `^[a-zA-Z0-9_-]{1,50}$`
- ✅ **Bug 12**: Logger rotativo por fecha (`TimedRotatingFileHandler`, rotación diaria)
- ✅ **Bug 13**: Health check endpoint ya existía en `main.py` (`GET /health`)

---

## Completado (Fase 2: Auditoría — 2026-07-15)

### Seguridad (13 items)
- ✅ **C1**: Port mismatch docker-compose corregido
- ✅ **C2**: Password PostgreSQL externo en docker-compose
- ✅ **C3**: API keys postergadas (usuario decidirá rotar después)
- ✅ **C4**: CORS explícito con warning en producción
- ✅ **C5**: Rate limiting por IP (10 req/min)
- ✅ **C6**: Autenticación por API key en producción
- ✅ **A8**: Credenciales DB enmascaradas en logs
- ✅ **A9**: SSRF mitigado
- ✅ **A10**: Info sensible eliminada de mensajes de error
- ✅ **A11**: CSP headers implementados
- ✅ **B2**: Log injection prevenido
- ✅ **B5**: Host seguro en development (127.0.0.1)
- ✅ **B14**: Healthcheck PG con contraseña

### Rendimiento (12 items)
- ✅ **C7**: Event loop desbloqueado con `run_in_executor`
- ✅ **C8**: Circuit breaker en FallbackProvider (5 fallos → 60s)
- ✅ **A12**: Memoria liberada después de guardar imagen
- ✅ **A14**: Circuit breaker implementado
- ✅ **A15**: Gemini client singleton
- ✅ **A16**: S3 client singleton
- ✅ **A17**: Umbral Otsu optimizado con `histogram()`
- ✅ **M12**: SQLite con `pool_pre_ping`
- ✅ **M13**: Cache de preprocesamiento OCR
- ✅ **M14**: Compresión de imagen antes de APIs (>1MB)
- ✅ **M15**: Upload optimizado

### Calidad (15 items)
- ✅ **C9**: `monto` "0" ya no se excluye
- ✅ **C10**: MIME type detectado desde extensión
- ✅ **C11**: ComprobanteResponse reemplaza monkey-patching
- ✅ **C12**: 32 tests (antes 15)
- ✅ **C13**: `create_all()` en startup event
- ✅ **A18**: Regex extraídos a `ocr/parsers.py`
- ✅ **A19**: Regex pre-compilados
- ✅ **A20**: Excepciones de storage envueltas
- ✅ **M1**: Import `re` a nivel de módulo
- ✅ **M4**: `load_dotenv()` una sola vez
- ✅ **M7**: Dead code eliminado (`to_dict`)
- ✅ **M16**: `cors_origins` type hint explícito
- ✅ **M17**: `datetime.now(timezone.utc)`
- ✅ **M18**: OCR status en respuesta API
- ✅ **M20**: Estado global mutable refactorizado

### Arquitectura (8 items)
- ✅ **A1**: URL S3 compatible con servicios custom
- ✅ **A2**: Temp files limpiados con `try/finally`
- ✅ **A3**: Versión dinámica en health check
- ✅ **A4**: `service.py` no conoce nombre del backend
- ✅ **A5**: Factories con registro dinámico
- ✅ **A6**: Config consolidada en ServerConfig
- ✅ **A7**: Limpieza en abstracción `StorageProvider`
- ✅ **M3**: `PROJECT_ROOT` consolidado en `config/common.py`

### Deploy (8 items)
- ✅ **A21**: Dockerfile con `ENV=production`
- ✅ **A22**: Procfile compatible con Heroku
- ✅ **A23**: Health check verifica BD
- ✅ **M23**: Dockerfile con HEALTHCHECK
- ✅ **M24**: `.dockerignore` completo
- ✅ **M25**: Healthcheck para servicio sami
- ✅ **M26**: Procfile install deps
- ✅ **B1**: Logger handler en tests

### Seguridad (3 items)
- ✅ **M9**: Secrets con `__repr__` redactado
- ✅ **M11**: SQLite pool_pre_ping
- ✅ **B11+B12**: Validación de credenciales al inicio

---

## Pendientes (3 items menores)

### B6: `os.path.exists()` por request en Tesseract
`ocr/tesseract_provider.py:124` ejecuta `os.path.exists()` en cada request para verificar el binario antes de ejecutar OCR.
**Impacto**: ~1ms overhead, despreciable. **Prioridad**: Baja.

### B7: Configuración PG incompleta
`database/backends/postgres.py` no configura `max_overflow`, `pool_timeout`, `pool_recycle`.
**Impacto**: Funciona actualmente, es mejora menor. **Prioridad**: Baja.

### B8: IO disco en cada log entry
`config/logger.py` escribe a disco en cada llamada a log.
**Mitigación**: Ya usa `TimedRotatingFileHandler` con buffer. **Prioridad**: Baja.

---

## Auditoría 2026-07-16 — Pendientes de optimización (7 items)

Hallazgos detectados durante la auditoría de flujo OCR. Los items 1 y 2 ya están resueltos.

### ✅ Resuelto 1 — Doble I/O en upload (`main.py`)
Streaming 8KB a temp file + re-lectura completa a RAM para validar. Se cambió a `imagen.read()` completo y `write_bytes()` directo a UUID. Sin temp file, sin re-lectura.

### ✅ Resuelto 2 — `proveedor` no se persistía en BD
`OCRResult.proveedor` se excluía del `model_dump` en `service.py:81`. Se renombró a `ocr`, se agregó columna en `database/models.py` y se eliminó el `exclude`. API no expone el campo.

### #3 — Storage factory crea instancia por request (`storage/__init__.py:59`)
`get_storage_backend()` crea un nuevo objeto en cada llamada (por request). Los clientes internos (S3, Gemini) sí son singleton internos, pero `LocalStorageProvider` se instancia centenares de veces sin necesidad.

**Archivo**: `storage/__init__.py`
**Contexto**: `get_storage_backend()` hace `return cls()` siempre. Los providers internos mantienen su propio singleton por módulo. El fix sería cachear la instancia igual que `get_ocr_engine()`.

### #4 — Compresión en OCRSpace aunque la imagen no lo requiera (`ocr/ocrspace_provider.py:68-70`)
Se llama `comprimir_imagen()` siempre antes de enviar a OCR.space. Si la imagen está por debajo de los umbrales (`activar_si_excede_bytes=1MB`), la compresión es no-op pero igual abre la imagen con PIL para verificarlo.

**Archivos**: `ocr/ocrspace_provider.py`, `ocr/gemini_provider.py`
**Contexto**: Ambos providers online llaman `comprimir_imagen()` incondicionalmente. Podría optimizarse para evitar el overhead de PIL en imágenes chicas (<100KB).

### #5 — Validación de API key postergada (`ocr/__init__.py:54-59`)
`_validar_configuracion()` solo loggea un warning si falta GEMINI_API_KEY o OCRSPACE_API_KEY, pero no evita la ejecución. El error real se descubre cuando el provider intenta la llamada HTTP.

**Archivo**: `ocr/__init__.py`
**Contexto**: La validación debería lanzar una excepción temprana si el proveedor seleccionado no tiene su API key configurada, en lugar de esperar al timeout HTTP.

### #6 — Sin timeouts explícitos en storage remoto (`storage/s3.py:78`, `storage/cloudinary.py:50`)
`resolver_ruta()` en S3 y Cloudinary usa `requests.get(ruta, timeout=30)` pero la conexión HTTP puede colgarse si el endpoint es lento, bloqueando el worker de Uvicorn.

**Archivos**: `storage/s3.py`, `storage/cloudinary.py`
**Contexto**: Ambos usan `requests.get()` sin timeout de conexión explícito. Agregar `timeout=(connect, read)`.

### #7 — Cache Tesseract usa `tobytes()` completo (`ocr/tesseract_provider.py:133`)
`hashlib.md5(img.tobytes())` carga toda la imagen a RAM para generar la clave de caché. En imágenes grandes (~4K px), duplica el uso de memoria momentáneamente.

**Archivo**: `ocr/tesseract_provider.py`
**Contexto**: La línea `cache_key = hashlib.md5(img.tobytes()).hexdigest()` serializa todo el bitmap. Alternativa: usar `img.tobytes()[:4096]` (primeros 4KB de pixeles) o `xxhash` para un hash rápido sin recorrer toda la imagen.

### #8 — Parser Gemini con mapeo no documentado (`ocr/gemini_provider.py:150-157`)
Gemini mapea `cajero` → `transfiere` y `no_venta` → `no_comprobante` como fallback, pero no hay tests ni documentación de estos campos alternativos. Cualquier cambio futuro en el prompt de Gemini puede romper el mapeo silenciosamente.

**Archivo**: `ocr/gemini_provider.py`
**Contexto**: Líneas 150-157: `datos.get("transfiere") or datos.get("cajero")`. Los nombres alternativos deberían estar documentados o en un TOML.

---

## Prioridad alta (funcionalidades futuras)

### 1. Dashboard web admin
Interfaz web para que el operador (tú) pueda:
- Ver comprobantes por cliente (`cliente_id`)
- Reprocesar OCR de imágenes fallidas
- Exportar datos a CSV
- Ver estadísticas de uso por cliente

**Sugerencia**: FastAPI + Jinja2 o React liviano. Misma BD, solo consultas.

### 2. Canales de entrada configurables
Hoy solo entra vía HTTP (POST /api/upload). Debería soportar:

- **WhatsApp** (Twilio / WhatsApp Business API)
- **Telegram** (Bot API)
- **Email** (IMAP listener)

**Patrón**: similar a OCR/storage — un provider por canal:
```
canales/
├── __init__.py    ← factoría
├── base.py        ← CanalProvider abstracto
├── http.py        ← el actual (POST /api/upload)
├── whatsapp.py    ← futuro
├── telegram.py    ← futuro
└── email.py       ← futuro
```

### 3. Autenticación multi-cliente
- Login por cliente (JWT o API keys)
- Aislamiento real: cada cliente solo ve sus propios datos
- Opcional: esquemas separados por cliente en PostgreSQL

---

## Prioridad media

### 4. Reprocesamiento batch
Endpoint o script que reprocesa imágenes cuyo OCR falló,
usando un proveedor diferente.

### 5. Facturación
Contador de requests por cliente. Ideal para modelo SaaS.

### 6. Notificaciones
Alertar al cliente cuando un comprobante es procesado (vía el canal que usó).

### 7. PWA no funciona offline
`static/sw.js` es un esqueleto vacío (no cachea nada). `manifest.json` tiene `"icons": []`.
La experiencia "PWA" no existe realmente. **Fix**: Implementar Service Worker con estrategia
"Network First, fallback to cache" + agregar iconos al manifest.

---

## Cómo contribuir / retomar

Cada item tiene un número. Cuando quieras retomar, dile al agente:
"Trabajemos en el punto 3 del BACKLOG" o similar.
