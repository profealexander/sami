# 📋 Auditoría de Producción — SAMI v2.2.0

**Fecha:** 2026-07-14  
**Auditor:** Claude Code  
**Estado del repo:** Git con blobs perdidos (ver sección final)  
**Archivos auditados:** 23 (lectura completa)

---

## 🚨 BLOCKERS — No desplegar sin fix

### 1. Port mismatch en docker-compose.yml
- **Archivo:** `docker-compose.yml:5`
- **Código:** `ports: "7000:7000"`
- **Problema:** El app escucha en `PORT=8000` por defecto pero Docker mapea 7000
- **Impacto:** `docker compose up` no funcionará con la config actual. Imposible acceder al servicio.
- **Fix:** Cambiar a `ports: "8000:8000"` o agregar `PORT=7000` al `.env` de Docker

### 2. Password de PostgreSQL hardcodeado
- **Archivo:** `docker-compose.yml:20`
- **Código:** `POSTGRES_PASSWORD: sami_secret`
- **Problema:** Credenciales de BD expuestas en el repo
- **Impacto:** Cualquier persona con acceso al repo obtiene acceso a la BD
- **Fix:** Usar variable de entorno `${POSTGRES_PASSWORD}` o Docker secrets

### 3. Regex doblemente anclado en cliente_id
- **Archivo:** `utils/upload_validator.py:125`
- **Código:** `re.fullmatch(r"^[a-zA-Z0-9_-]{1,50}$", cliente_id)`
- **Problema:** `re.fullmatch()` ya fuerza match completo del string. Los `^` y `$` son redundantes y pueden causar comportamiento inesperado con `re.MULTILINE`
- **Impacto:** Posibles falsos negativos en validación de cliente_id
- **Fix:** `re.fullmatch(r"[a-zA-Z0-9_-]{1,50}", cliente_id)`

---

## 🔴 HIGH — Bugs que se manifestarán en producción

### 4. MIME type hardcodeado en Gemini
- **Archivo:** `ocr/gemini_provider.py:93`
- **Código:** `mime_type="image/jpeg"`
- **Problema:** Si el usuario sube WebP o PNG (permitidos por validador), Gemini recibe `image/jpeg`
- **Impacto:** Degradación de OCR o errores con imágenes no-JPEG
- **Fix:** Detectar formato real con `PIL.Image.open()` y mapear a MIME type correcto

### 5. URL S3 ignora endpoint custom
- **Archivo:** `storage/s3.py:43`
- **Código:** `url = f"https://{cfg.s3_bucket}.s3.{cfg.s3_region}.amazonaws.com/{key}"`
- **Problema:** URL construida asume endpoint AWS nativo, ignora `s3_endpoint` configurado
- **Impacto:** Con Backblaze B2 o MinIO, URLs generadas están rotas → imposible recuperar imágenes
- **Fix:** Usar `client.generate_presigned_url()` o construir URL desde `cfg.s3_endpoint`

### 6. Temp files no limpiados en error de OCR
- **Archivo:** `service.py:77`
- **Código:** `_limpiar_temporal()` llamado después del bloque try/except
- **Problema:** Si storage es S3/Cloudinary y OCR falla, archivo temporal descargado nunca se elimina
- **Impacto:** Acumulación de archivos temporales hasta llenar disco
- **Fix:** Mover `_limpiar_temporal()` a bloque `finally` o usar context manager

### 7. Versión hardcodeada en health check
- **Archivo:** `main.py:51`
- **Código:** `"version": "2.2.0"`
- **Problema:** No coincide con `pyproject.toml` (2.0.0). Hardcodeada, requiere update manual
- **Impacto:** Monitoreo de producción reporta versión incorrecta
- **Fix:** Leer desde `importlib.metadata.version("sami")` o constante compartida

### 8. DDL ejecutado al importar models.py
- **Archivo:** `database/models.py:39`
- **Código:** `Base.metadata.create_all(bind=engine)`
- **Problema:** Cada `import database` ejecuta DDL contra la BD
- **Impacto:** En tests con DB efímera o migraciones reales, causa conflictos o lentitud innecesaria
- **Fix:** Mover a script de init/migración o lifecycle event de FastAPI

---

## 🟡 MEDIUM — Deuda técnica conocida (del BACKLOG)

### 9. Código OCR duplicado
- **Archivos:** `ocr/tesseract_provider.py:139` + `ocrspace_provider.py:137`
- **Líneas:** ~80 líneas c/u (`MESES_ES`, `MESES_FALLBACK`, `_parsear_campos()`)
- **Problema:** Código casi idéntico en dos archivos
- **Impacto:** Corregir un patrón requiere hacerlo en ambos archivos
- **Fix:** Extraer a `ocr/parsers.py` con funciones compartidas

### 10. Import innecesario dentro de función
- **Archivo:** `utils/upload_validator.py:124`
- **Código:** `import re` dentro de `validar_cliente_id()`
- **Problema:** Import a nivel de función en lugar de módulo
- **Impacto:** Cada llamada re-importa módulo (ineficiente) y rompe consistencia
- **Fix:** Mover `import re` al inicio del archivo

### 11. OCR bloquea event loop
- **Archivo:** `main.py` → handler `subir_comprobante`
- **Problema:** Llamadas OCR síncronas (3-10s) dentro de handler async
- **Impacto:** Con 2+ requests simultáneos, el segundo espera al primero. Throughput degradado.
- **Fix:** Usar `asyncio.to_thread(engine.extraer_campos, ruta)` o `run_in_executor()`

### 12. Campos OCR no persistidos
- **Archivo:** `database/models.py` → modelo `Comprobante`
- **Campos:** `monto` y `destinatario`
- **Problema:** Se extraen por OCR pero las columnas no existen en la tabla
- **Impacto:** Datos se pierden silenciosamente. `service.py:111-115` los adjunta como atributos temporales
- **Fix:** Agregar columnas `monto` y `destinatario` al modelo

---

## 🟢 LOW — Observaciones

### 13. Dockerfile corre como root
- **Archivo:** `Dockerfile`
- **Problema:** No especifica usuario, corre como root por defecto
- **Impacto:** Riesgo de seguridad menor (aceptable para MVP)
- **Fix:** Agregar `USER nobody` al final o usar imagen base no-root

### 14. Dockerfile sin HEALTHCHECK
- **Archivo:** `Dockerfile`
- **Problema:** `docker compose` depende de healthcheck de `db` pero no del propio SAMI
- **Impacto:** Docker no detecta si SAMI está vivo pero fallando
- **Fix:** Agregar `HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1`

### 15. Parseo frágil de reload
- **Archivo:** `config/server.py:73`
- **Código:** `reload=os.getenv("RELOAD", str(reload_default)).lower() == "true"`
- **Problema:** Solo acepta "true" minúsculas, no "True" o "TRUE"
- **Impacto:** Configuración no intuitiva
- **Fix:** Usar parsing más robusto (ej: `in ("true", "1", "yes")`)

### 16. Handler de error global redundante
- **Archivo:** `main.py:155` → `error_global`
- **Problema:** FastAPI ya maneja excepciones no capturadas. Además, `subir_comprobante` tiene `except Exception` propio
- **Impacto:** Código muerto/redundante
- **Fix:** Eliminar `error_global` o documentar por qué es necesario

### 17. .gitignore no incluye logs/
- **Archivo:** `.gitignore`
- **Problema:** Ignora `*.log` en raíz pero logging escribe en `logs/sami.log`
- **Impacto:** Directorio `logs/` se commitea accidentalmente
- **Fix:** Agregar `logs/` al `.gitignore`

---

## 🧪 Testing — Cobertura actual

### Archivos con tests
- ✅ `tests/test_upload_validator.py` — 15 tests (validación de uploads)

### Archivos SIN tests
- ❌ `ocr/gemini_provider.py` — Sin tests
- ❌ `ocr/tesseract_provider.py` — Sin tests
- ❌ `ocr/ocrspace_provider.py` — Sin tests
- ❌ `ocr/fallback.py` — Sin tests
- ❌ `storage/local.py` — Sin tests
- ❌ `storage/s3.py` — Sin tests
- ❌ `storage/cloudinary.py` — Sin tests
- ❌ `service.py` — Sin tests
- ❌ `database/engine.py` — Sin tests
- ❌ `main.py` (API endpoints) — Sin tests de integración

### Recomendación
Antes de producción, agregar al menos:
1. Tests de API con FastAPI TestClient (endpoints /health, /api/upload)
2. Tests unitarios para cada OCR provider (mock API calls)
3. Tests unitarios para cada storage backend (mock uploads)
4. Test de integración con imagen real

---

## ⚠️ Estado del repositorio Git

```
$ git fsck
missing blob 2e3cdd1c
missing blob 7ba46f94
missing blob 1249e372
```

**Problema:** 3 blobs perdidos en el repo. `git diff` falla con "unable to read" errors.

**Causa probable:** Corrupción local del repo (posible por disco, sync, o interrupción de git)

**Impacto:** 
- No se pueden ver diffs de commits previos
- `database/models.py` muestra como modificado pero no se puede ver el diff exacto

**Fix recomendado:**
1. Clonar desde remoto: `git clone <repo-url> && cd sami`
2. O ejecutar: `git fetch origin && git reset --hard origin/main`
3. Verificar con: `git fsck` (debe estar limpio)

---

## 📋 Plan de acción (prioridad)

| # | Acción | Archivo | Líneas | Dificultad |
|---|--------|---------|--------|------------|
| 1 | Fix port mismatch | `docker-compose.yml` | 1 | Trivial |
| 2 | Sacar password de BD | `docker-compose.yml` | 2 | Trivial |
| 3 | Fix regex cliente_id | `utils/upload_validator.py:125` | 1 | Trivial |
| 4 | Fix MIME type Gemini | `ocr/gemini_provider.py` | 3 | Fácil |
| 5 | Fix URL S3 custom | `storage/s3.py` | 5 | Fácil |
| 6 | Move temp cleanup to finally | `service.py` | 3 | Fácil |
| 7 | Fix versión hardcodeada | `main.py` | 2 | Fácil |
| 8 | Move create_all out of import | `database/models.py` | 5 | Medio |
| 9 | Reparar repo git | - | - | Medio |

**Total estimado:** ~30 minutos para fixes 1-8

---

## 📊 Resumen ejecutivo

- **3 blockers críticos** que impiden despliegue
- **5 bugs de alta severidad** que causarán problemas en producción
- **4 items de deuda media** conocidos (del BACKLOG)
- **5 observaciones menores** de calidad
- **~90% sin cobertura de tests** (solo 1 archivo testeado)
- **Repo git corrupto** requiere reparación antes de continuar

**Veredicto:** ⚠️ **NO LISTO PARA PRODUCCIÓN** sin fixear blockers #1-3

---

## 🔗 Referencias

- BACKLOG.md: Lista completa de 19 items pendientes
- CLAUDE.md: Guía para futuras sesiones de Claude Code
- `database/README.md`: Cómo extender la capa de BD
- `ocr/PROVEEDORES_OCR.md`: Documentación de proveedores OCR
