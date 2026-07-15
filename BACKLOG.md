# BACKLOG — SAMI v2

Proximos pasos y funcionalidades pendientes.

---

## Completado (Fase 1 — 2026-07-14)

- ✅ **Bug 2**: `imghdr` deprecado reemplazado por `PIL.Image` en `upload_validator.py`
- ✅ **Bug 7**: Validación de `cliente_id` con regex `^[a-zA-Z0-9_-]{1,50}$`
- ✅ **Bug 12**: Logger rotativo por fecha (`TimedRotatingFileHandler`, rotación diaria)
- ✅ **Bug 13**: Health check endpoint ya existía en `main.py` (`GET /health`)

---

## Prioridad alta

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

### 3. Persistir campos OCR extendidos en BD (Bug 1)
`monto` y `destinatario` se extraen por OCR pero NO se guardan en la tabla `comprobantes`.
Se pierden silenciosamente. Agregar columnas `monto`, `destinatario`, `texto_completo` al modelo.
Luego mejorar regex de `ocrspace_provider.py` para extraer correctamente estos campos.

### 4. Event loop bloqueado durante OCR (Bug 4)
Las llamadas OCR (3-10 segundos) se ejecutan sincrónicamente dentro de handlers FastAPI async,
bloqueando el event loop. Si llegan 2 requests simultáneos, el segundo espera al primero.
**Fix**: Usar `asyncio.to_thread()` o `run_in_executor()` para mover OCR a thread pool.

### 5. Código OCR duplicado (Bug 5)
`tesseract_provider.py` y `ocrspace_provider.py` tienen ~80 líneas de regex casi idénticas
en `_parsear_campos()`. Si se corrige un patrón en uno, hay que corregirlo en el otro.
**Fix**: Extraer a `ocr/parsers.py` con funciones compartidas.

### 6. Temp files no limpiados en error (Bug 6)
En `service.py`, si el storage es S3/Cloudinary y el OCR falla después de descargar la imagen
remota, el archivo temporal queda huérfano en disco. `_limpiar_temporal` existe pero no se
llama en el path de error. **Fix**: Usar `try/finally` o context manager.

---

## Prioridad media

### 7. Rate limiting por cliente (Bug 14)
Proteger el server de abusos. Ya hay placeholder en `config/server.py` (`rate_limit: int = 100`)
pero no hay middleware que lo implemente. Implementar con `slowapi` o middleware propio,
limitando por `cliente_id`.

### 8. CORS seguro en producción (Bug 8)
`CORS_ORIGINS=*` funciona en dev pero es inseguro en producción.
Agregar warning en `run.py` si `ENV=production` y `cors_origins == ["*"]`.

### 9. Testing automatizado
- Tests unitarios para cada provider OCR
- Tests de integración con imágenes de muestra
- Tests de API (FastAPI TestClient)

### 10. Migración a PostgreSQL en producción
Instrucciones y script de migración desde SQLite local a PostgreSQL cloud.
`database.py` ya soporta ambos vía `DATABASE_URL`.

---

## Prioridad baja / futuro

### 11. Autenticación multi-cliente
- Login por cliente (JWT o API keys)
- Aislamiento real: cada cliente solo ve sus propios datos
- Opcional: esquemas separados por cliente en PostgreSQL

### 12. Reprocesamiento batch
Endpoint o script que reprocesa imágenes cuyo OCR falló,
usando un proveedor diferente.

### 13. Facturación
Contador de requests por cliente. Ideal para modelo SaaS.

### 14. Notificaciones
Alertar al cliente cuando un comprobante es procesado (vía el canal que usó).

### 15. PWA no funciona offline (Bug 9)
`static/sw.js` es un esqueleto vacío (no cachea nada). `manifest.json` tiene `"icons": []`.
La experiencia "PWA" no existe realmente. **Fix**: Implementar Service Worker con estrategia
"Network First, fallback to cache" + agregar iconos al manifest.

### 16. Imagen leída múltiples veces (Bug 10)
Flujo actual: `await imagen.read()` → `validar_archivo()` → `backend.guardar()` → OCR relee
desde disco. Son 3-4 operaciones sobre los mismos bytes. Con imágenes de 10MB y requests
concurrentes, el uso de RAM puede dispararse. **Fix**: Pasar bytes directamente al OCR.

---

## Técnico / deuda

### 17. Logging estructurado
Reemplazar `print()` por logging con `loguru` o `structlog`.
Niveles: debug, info, warning, error. Rotación de archivos.
(Parcialmente hecho: `config/logger.py` ya usa logging stdlib con rotación por fecha)

### 18. Regex no compilados (Bug 11)
`_parsear_campos()` compila ~15 regex en cada llamada. **Fix**: Compilar una vez como
constantes de clase o a nivel de módulo con `re.compile()`.

### 19. Gemini falla silenciosamente (Bug 3)
Si Gemini devuelve texto pero no es JSON válido, `_parsear_json()` retorna `{"texto_completo": texto}`
sin lanzar excepción. El fallback automático a Tesseract **no se activa** porque no hay error.
**Nota**: Ignorado por ahora (Gemini no se usa como principal ni fallback).

---

## Cómo contribuir / retomar

Cada item tiene un número. Cuando quieras retomar, dile al agente:
"Trabajemos en el punto 3 del BACKLOG" o similar.
