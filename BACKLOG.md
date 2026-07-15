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

---

## Prioridad media

### 4. Rate limiting por cliente (Bug 14)
Proteger el server de abusos. Ya hay placeholder en `config/server.py` (`rate_limit: int = 100`)
pero no hay middleware que lo implemente. Implementar con `slowapi` o middleware propio,
limitando por `cliente_id`.

### 5. CORS seguro en producción (Bug 8)
`CORS_ORIGINS=*` funciona en dev pero es inseguro en producción.
Agregar warning en `run.py` si `ENV=production` y `cors_origins == ["*"]`.

### 6. Testing automatizado
- Tests unitarios para cada provider OCR
- Tests de integración con imágenes de muestra
- Tests de API (FastAPI TestClient)

### 7. Migración a PostgreSQL en producción
Instrucciones y script de migración desde SQLite local a PostgreSQL cloud.
`database.py` ya soporta ambos vía `DATABASE_URL`.

---

## Prioridad baja / futuro

### 8. Autenticación multi-cliente
- Login por cliente (JWT o API keys)
- Aislamiento real: cada cliente solo ve sus propios datos
- Opcional: esquemas separados por cliente en PostgreSQL

### 9. Reprocesamiento batch
Endpoint o script que reprocesa imágenes cuyo OCR falló,
usando un proveedor diferente.

### 10. Facturación
Contador de requests por cliente. Ideal para modelo SaaS.

### 11. Notificaciones
Alertar al cliente cuando un comprobante es procesado (vía el canal que usó).

---

## Técnico / deuda

### 12. Logging estructurado
Reemplazar `print()` por logging con `loguru` o `structlog`.
Niveles: debug, info, warning, error. Rotación de archivos.
(Parcialmente hecho: `config/logger.py` ya usa logging stdlib con rotación por fecha)

---

## Cómo contribuir / retomar

Cada item tiene un número. Cuando quieras retomar, dile al agente:
"Trabajemos en el punto 3 del BACKLOG" o similar.
