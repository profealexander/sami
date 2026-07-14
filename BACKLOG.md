# BACKLOG — SAMI v2

Proximos pasos y funcionalidades pendientes.

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

---

## Prioridad media

### 3. Rate limiting por cliente
Proteger el server de abusos. Ya hay placeholder en `config/server.py`.
Implementar con `slowapi` o middleware propio, limitando por `cliente_id`.

### 4. Testing automatizado
- Tests unitarios para cada provider OCR
- Tests de integración con imágenes de muestra
- Tests de API (FastAPI TestClient)

### 5. Migración a PostgreSQL en producción
Instrucciones y script de migración desde SQLite local a PostgreSQL cloud.
`database.py` ya soporta ambos vía `DATABASE_URL`.

---

## Prioridad baja / futuro

### 6. Autenticación multi-cliente
- Login por cliente (JWT o API keys)
- Aislamiento real: cada cliente solo ve sus propios datos
- Opcional: esquemas separados por cliente en PostgreSQL

### 7. Reprocesamiento batch
Endpoint o script que reprocesa imágenes cuyo OCR falló,
usando un proveedor diferente.

### 8. Facturación
Contador de requests por cliente. Ideal para modelo SaaS.

### 9. Notificaciones
Alertar al cliente cuando un comprobante es procesado (vía el canal que usó).

---

## Técnico / deuda

### 10. Rate limiting funcional
`config/server.py` tiene `rate_limit: int = 100` pero no hay middleware.
Implementar con slowapi o custom middleware.

### 11. Logging estructurado
Reemplazar `print()` por logging con `loguru` o `structlog`.
Niveles: debug, info, warning, error. Rotación de archivos.

### 12. Health check endpoint
`GET /health` para monitoreo del VPS/Railway/Koyeb.

---

## Cómo contribuir / retomar

Cada item tiene un número. Cuando quieras retomar, dile al agente:
"Trabajemos en el punto 2 del BACKLOG" o similar.
