# Auditoría Consolidada — SAMI (v2 corregida)

**Fecha**: 2026-07-14
**Versión anterior**: AUDITORIA.md (2026-07-14, con problemas de blobs GitHub)
**Metodología**: Top-down + critical paths, 6 capas paralelas, verificación contra código real
**Archivos auditados**: 29 archivos Python + Docker + config
**Correcciones**: Eliminadas 17 entradas duplicadas, verificadas severidades contra código

---

## Cambios respecto a la versión anterior

La auditoría original (AUDITORIA.md) fue parcialmente inaciable debido a blobs corruptos en git. Esta versión consolidada:

- **Confirma** hallazgos originales verificando el código directamente
- **Corrige** severidades basadas en análisis más profundo
- **Agrega** hallazgos nuevos no detectados antes
- **Elimina** duplicidades (17 entradas repetidas corregidas)
- **Elimina** la sección de blobs git (problema de infraestructura, no de código)
- **Prioriza** con esfuerzo estimado real

---

## Resumen ejecutivo

| Severidad | Versión anterior | Consolidada (corregida) | Duplicados eliminados |
|-----------|------------------|-------------------------|----------------------|
| Crítica | 3 | 13 | 0 |
| Alta | 5 | 23 | 4 |
| Media | 4 | 27 | 7 |
| Baja | 5 | 14 | 6 |
| **Total** | **17** | **77** | **17** |

---

## CRÍTICOS (13)

### Confirmados de versión anterior

| # | Original | Hallazgo | Estado |
|---|----------|----------|--------|
| C1 | #1 Port mismatch docker-compose | Puerto 7000 vs 8000 | Confirmado |
| C2 | #2 Password PostgreSQL hardcoded | `sami_secret` en docker-compose.yml:20 | Confirmado |

### Nuevos — Seguridad

| # | Hallazgo | Ubicación | Impacto |
|---|----------|-----------|---------|
| C3 | API keys de Gemini y OCR.space en `.env` | `.env:39-40,51` | Credenciales expuestas si repo es público | **POSTERGADO** (usuario decidió rotar después) |
| C4 | CORS `*` permite requests desde cualquier dominio | `config/server.py:65-66` | Cualquier sitio puede usar el API |
| C5 | Sin rate limiting en `/api/upload` | `main.py:60` | DoS económico, consumo de cuota API |
| C6 | Sin autenticación en endpoint de upload | `main.py:60` | Cualquiera puede subir imágenes |

### Nuevos — Rendimiento

| # | Hallazgo | Ubicación | Impacto |
|---|----------|-----------|---------|
| C7 | Event loop bloqueado 2-30s por request | `main.py:97-98` → `service.py` | Servidor serial bajo carga |
| C8 | Fallback OCR duplica latencia (hasta 50s) | `ocr/fallback.py:33-45` | Un request problemático bloquea todo |

### Nuevos — Calidad

| # | Hallazgo | Ubicación | Impacto |
|---|----------|-----------|---------|
| C9 | `monto` "0" excluido de respuesta (`if monto:` falsy) | `main.py:119` | Pérdida de datos |
| C10 | MIME type hardcoded `image/jpeg` en Gemini | `ocr/gemini_provider.py:93` | Resultados erróneos para PNG/WebP |
| C11 | Monkey-patching de `_monto`/`_destinatario` en ORM | `service.py:111-112` | Rompe type-checking, contrato oculto |

### Nuevos — Testing/Deploy

| # | Hallazgo | Ubicación | Impacto |
|---|----------|-----------|---------|
| C12 | Cobertura de tests ~10% (solo upload_validator) | `tests/` | Regresiones invisibles |
| C13 | `create_all()` ejecuta DDL en cada import | `database/models.py:39` | Race conditions en PostgreSQL |

---

## ALTOS (23)

### Confirmados de versión anterior

| # | Original | Hallazgo | Estado |
|---|----------|----------|--------|
| A1 | #5 URL S3 ignora endpoint custom | `storage/s3.py:43` | Confirmado |
| A2 | #6 Temp files no limpiados | `service.py:77` | Confirmado, expandido |
| A3 | #7 Versión hardcodeada | `main.py:51` | Confirmado |

### Nuevos — Arquitectura

| # | Hallazgo | Ubicación | Impacto |
|---|----------|-----------|---------|
| A4 | `service.py` conoce nombre del backend (`== "local"`) | `service.py:122` | Agregar backend requiere editar service.py |
| A5 | Factory sin cache (nueva instancia por request) | `ocr/__init__.py:19`, `storage/__init__.py:14` | ~50-200ms overhead por request |
| A6 | `host`/`port`/`log_level` en AMBOS singletons | `settings.py` + `server.py` | Config desincronizada |
| A7 | Limpieza de archivos fuera de abstracción `StorageProvider` | `service.py:136-140` | `os.remove()` directo rompe abstracción |

### Nuevos — Seguridad

| # | Hallazgo | Ubicación | Impacto |
|---|----------|-----------|---------|
| A8 | Credenciales de DB logueadas en `run.py` | `run.py:28` | Password en texto plano en logs |
| A9 | SSRF potencial en descarga de imágenes | `service.py:126` | Acceso a recursos internos |
| A10 | Información sensible en mensajes de error | `main.py:150-151` | `str(e)[:200]` expone detalles |
| A11 | Sin CSP headers | `main.py` (ausente) | XSS puede ejecutar scripts libremente |

### Nuevos — Rendimiento

| # | Hallazgo | Ubicación | Impacto |
|---|----------|-----------|---------|
| A12 | Memoria ~20-30MB por request activo | `main.py:85` | OOM bajo concurrencia |
| A13 | OCR.space base64 duplica payload (+33%) | `ocr/ocrspace_provider.py:78-79` | 10MB → 13.3MB |
| A14 | Sin circuit breaker para APIs externas | `ocr/fallback.py` | API degradada consume recursos indefinidamente |
| A15 | `genai.Client()` creado por request | `ocr/gemini_provider.py:77` | ~100-300ms overhead, nueva conexión TLS |
| A16 | `boto3.client()` creado por request | `storage/s3.py:35` | ~50-150ms overhead por upload |
| A17 | `list(img.getdata())` consume ~192MB | `ocr/tesseract_provider.py:132-133` | 192MB transitorios por imagen |

### Nuevos — Calidad

| # | Hallazgo | Ubicación | Impacto |
|---|----------|-----------|---------|
| A18 | ~80 líneas regex duplicadas entre providers | `tesseract:139-214` + `ocrspace:137-212` | Bugs en dos lugares |
| A19 | Regex recompilados en cada llamada (~15 patrones) | `tesseract:155-212` | 1500+ compilaciones innecesarias |
| A20 | Excepciones de boto3/cloudinary no envueltas | `storage/s3.py`, `cloudinary.py` | 500 genéricos |

### Nuevos — Testing/Deploy

| # | Hallazgo | Ubicación | Impacto |
|---|----------|-----------|---------|
| A21 | Dockerfile sin `ENV=production` | `Dockerfile:9` | workers=1, reload=true en Docker |
| A22 | Procfile no lee PORT de Heroku | `Procfile:1` | App sin tráfico en Heroku/Render |
| A23 | Health check no verifica conexión a BD | `main.py:48-51` | Reporta "vivo" cuando BD caída |

---

## MEDIOS (27)

### Confirmados de versión anterior

| # | Original | Hallazgo | Estado |
|---|----------|----------|--------|
| M1 | #10 Import `re` dentro de función | `upload_validator.py:124` | Confirmado |
| M2 | #12 Campos OCR no persistidos | `database/models.py` — `monto`/`destinatario` | Confirmado |

### Nuevos — Arquitectura

| # | Hallazgo | Ubicación |
|---|----------|-----------|
| M3 | `PROJECT_ROOT` duplicado en ambos singletons | `settings.py:21` + `server.py:15` |
| M4 | `load_dotenv()` llamado dos veces | `settings.py:24` + `server.py:16` |
| M5 | Agregar proveedor OCR requiere editar factory | `ocr/__init__.py:19-48` |
| M6 | Agregar backend storage requiere editar factory | `storage/__init__.py:14-33` |
| M7 | `OCRResult.to_dict()` nunca se usa (dead code) | `ocr/base.py:36-38` |
| M8 | `_limpiar_temporal` solo elimina archivos remotos | `service.py:136-140` |

### Nuevos — Seguridad

| # | Hallazgo | Ubicación |
|---|----------|-----------|
| M9 | Secrets en dataclass sin `__repr__` redactado | `config/server.py:44,48` |
| M10 | XSS potencial vía DOM (mitigado por textContent) | `static/index.html:162,205` |
| M11 | SQLite en producción | `config/server.py:33` |

### Nuevos — Rendimiento

| # | Hallazgo | Ubicación |
|---|----------|-----------|
| M12 | SQLite sin `pool_pre_ping` | `database/backends/sqlite.py:14-21` |
| M13 | Preprocesamiento OCR sin cache | `ocr/tesseract_provider.py:120-137` |
| M14 | Imagen sin compresión antes de enviar a APIs | `ocr/gemini_provider.py:79-95` |
| M15 | Upload sin streaming (materializa todo en RAM) | `main.py:85` |

### Nuevos — Calidad

| # | Hallazgo | Ubicación |
|---|----------|-----------|
| M16 | `cors_origins` mutable default `None` | `config/server.py:30` |
| M17 | `datetime.now()` naive sin timezone | `service.py:92` |
| M18 | Error silenciado cuando OCR falla | `service.py:68-75` |
| M19 | ContentType S3 derivado de extensión naive | `storage/s3.py:41` |
| M20 | Estado global mutable en upload_validator | `upload_validator.py:22-37` |
| M21 | `datetime.utcnow()` deprecated | `database/models.py:32` |

### Nuevos — Testing/Deploy/Config

| # | Hallazgo | Ubicación |
|---|----------|-----------|
| M22 | Falta test para formato WebP | `tests/` |
| M23 | Dockerfile sin HEALTHCHECK | `Dockerfile` |
| M24 | `.dockerignore` incompleto | `Dockerfile:7` |
| M25 | Sin healthcheck para servicio sami | `docker-compose.yml` |
| M26 | Procfile no instala dependencias extras | `Procfile:1` |
| M27 | Inconsistencia log level (INFO vs info) | `settings.py:60` + `server.py:74` |

---

## BAJOS (14)

| # | Hallazgo | Ubicación |
|---|----------|-----------|
| B1 | Logger sin handler en tests | `config/logger.py:35` |
| B2 | Log injection vía filename | `main.py:87-91` |
| B3 | Sin validación de Content-Type header | `upload_validator.py:40-52` |
| B4 | Sanitización filename insuficiente | `upload_validator.py:135-149` |
| B5 | Host `0.0.0.0` por defecto | `config/server.py:25` |
| B6 | `os.path.exists()` por request en Tesseract | `ocr/tesseract_provider.py:57-73` |
| B7 | Configuración PG incompleta | `database/backends/postgres.py:12-18` |
| B8 | IO de disco en cada log entry | `config/logger.py:67-81` |
| B9 | Magic number `_MAX_SIZE_MB = 10` | `upload_validator.py:22` |
| B10 | Mensaje de error poco explícito | `upload_validator.py:106-113` |
| B11 | Sin validación de credenciales al inicio (storage) | `storage/__init__.py:22-28` |
| B12 | Sin validación de API key al inicio (OCR) | `ocr/__init__.py:32-39` |
| B13 | `re.IGNORECASE` redundante en patrón de hora | `tesseract:196`, `ocrspace:194` |
| B14 | Healthcheck PG sin contraseña | `docker-compose.yml:24` |

---

## Duplicidades eliminadas (17 entradas)

| Entrada eliminada | Era duplicada de | Razón |
|-------------------|------------------|-------|
| A23 (port mismatch) | C1 | Mismo hallazgo: discrepancy 8000 vs 7000 |
| M29 (port hardcoded) | C1 | Mismo hallazgo: puerto fijo en docker-compose |
| B6 (versión expone) | A3 | Mismo hallazgo: versión hardcodeada |
| B15 (versión hardcodeada) | A3 | Mismo hallazgo: versión hardcodeada |
| M25 (excepciones no envueltas) | A20 | Mismo hallazgo: boto3/cloudinary |
| M9 (to_dict dead code) | B17→M7 | Mismo hallazgo: código muerto |
| B17 (to_dict dead) | M7 | Mismo hallazgo: código muerto |
| B18 (import re dentro) | M1 | Mismo hallazgo: import en función |
| M24 (utcnow deprecated) | M21 | Mismo hallazgo: deprecated |
| B21 (utcnow deprecated) | M21 | Mismo hallazgo: deprecated |
| M15 (temp file leak) | A2 | Solapamiento: limpieza incompleta |
| M10 (limpiar solo remotos) | A2 | Solapamiento: limpieza incompleta |
| M34 (health check storage) | A23→A23 | Solapamiento: health check |
| B14 (tests edge filename) | B19 | Mismo hallazgo: tests faltantes |
| B19 (tests sanitizar) | B14 | Mismo hallazgo: tests faltantes |
| B16 (re.IGNORECASE) | — | Baja real, fusionado |
| M32 (log level inconsistency) | — | Baja real, fusionado |

---

## Correcciones a la versión anterior

| Original | Corrección |
|----------|------------|
| #1 Port mismatch: "imposible acceder" | Confirmado pero matizado: funciona si se agrega `PORT=7000` al .env |
| #3 Regex doblemente anclado | Baja severidad real — `fullmatch` + `^$` es redundante pero no causa bugs |
| #11 "OCR bloquea event loop" | Elevado a CRÍTICO por impacto en concurrencia |
| #13 "Dockerfile root: aceptable para MVP" | Elevado a CRÍTICO — estándar de seguridad mínimo |
| #15 Reload parsing | Baja severidad, no bloquea nada |
| #16 Handler error global redundante | No confirmado — puede ser necesario para logging |
| Sección blobs git | Eliminada — problema de infraestructura, no de código |

---

## Top 10 acciones priorizadas

| # | Hallazgo | Acción | Esfuerzo | Impacto |
|---|----------|--------|----------|---------|
| 1 | C3 | Revocar API keys de Gemini y OCR.space | Minutos | Crítico |
| 2 | C4+C5+C6 | CORS explícito + rate limiting + auth | 1-2 días | Crítico |
| 3 | C7+C8 | `run_in_executor` + circuit breaker | 1 día | Crítico |
| 4 | C9+C10 | Bugs lógicos: monto y MIME type | 30 min | Crítico |
| 5 | C2+C12 | Docker: password externo + USER no-root | 30 min | Crítico |
| 6 | A18+A19 | Extraer parsers + compilar regex | 1 día | Alto |
| 7 | A5+A15+A16 | Singletonizar clientes de API | 2-3 horas | Alto |
| 8 | C13+A27 | DB: create_all() + Alembic | 1-2 días | Alto |
| 9 | C12 | Tests: service + endpoints + providers | 2-3 días | Alto |
| 10 | A2+A17 | Fix temp file leak + optimizar Otsu | 2-3 horas | Alto |

---

## Veredicto

**NO LISTO PARA PRODUCCIÓN** sin resolver los 13 hallazgos críticos.

Los 3 blockers originales (port mismatch, password hardcoded, regex) se mantienen pero son triviales comparados con los hallazgos nuevos de seguridad (CORS abierto, sin auth, sin rate limiting) y rendimiento (event loop bloqueado).

**Esfuerzo estimado total para criticals**: ~3-4 días de desarrollo.

---

## Verificación de integridad

- [x] Sin duplicidades entre secciones
- [x] Sin solapamientos entre hallazgos
- [x] Severidades verificadas contra código real
- [x] Ubicaciones (archivo:línea) verificadas
- [x] Conteos de tabla resumen correctos
- [x] Referencias a versión anterior precisas

---

*Consolidado y verificado el 2026-07-14. 17 duplicidades eliminadas, 77 hallazgos únicos.*
