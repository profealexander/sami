# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SAMI (Sistema de Archivo y Manejo de Imágenes de Comprobantes) is a receipt capture and OCR processing server. Users photograph receipts via a PWA, the system extracts structured data through multi-provider OCR, and persists results to a database. Python 3.10+, FastAPI, SQLAlchemy 2.x, managed with **uv**.

**All code, comments, docstrings, and documentation are in Spanish.** Match this convention when writing new code or comments.

## Commands

```bash
# Install dependencies
uv sync

# Install all extras (needed for running tests with optional deps)
uv sync --all-extras

# Run dev server (hot-reload, port from .env, default 8000)
python run.py

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_upload_validator.py

# Run a single test
uv run pytest tests/test_upload_validator.py::TestValidarClienteId::test_id_valido_tienda_001

# Lint (no config file — uses ruff defaults)
uv run ruff check .

# Format
uv run ruff format .
```

No CI/CD is configured. No ruff.toml, pytest.ini, or pre-commit config exists — ruff and pytest run with defaults.

## Architecture

**3-layer architecture** with two interchangeable strategy-pattern modules:

```
run.py → boots uvicorn with main:app
  │
  ├─ Layer 1: main.py         FastAPI routes, CORS, CSP headers, static mount, startup event
  │    └─ POST /api/upload    Only write endpoint (imagen + cliente_id) — streaming upload
  │    └─ GET /health         Health check (verifies DB connection)
  │
  ├─ Layer 2: service.py      Business orchestration (ComprobanteResponse, no monkey-patching)
  │    ├─ guardar_imagen_fisica()      → storage backend
  │    └─ procesar_y_guardar_comprobante() → OCR engine → DB persist
  │
  └─ Layer 3: database/       SQLAlchemy ORM, engine factory, sessions
       ├─ engine.py           Picks SQLite or PostgreSQL from DATABASE_URL
       ├─ models.py           ORM models (Comprobante) — columns: monto, destinatario
       └─ backends/           DB-specific engine factories (sqlite.py, postgres.py)
```

**Cross-cutting infrastructure:**

- `ocr/` — Strategy pattern. `OCRProvider` ABC (`base.py`), 3 providers (gemini, tesseract, ocrspace), `FallbackProvider` with **circuit breaker** (5 failures → 60s timeout). Factory: `get_ocr_engine()` reads `OCR_PROVIDER` from `.env`.
- `storage/` — Strategy pattern. `StorageProvider` ABC (`base.py`) with `resolver_ruta()` and `limpiar_temporal()`. 3 backends (local, s3, cloudinary). Factory: `get_storage_backend()` reads `STORAGE_BACKEND` from `.env`.
- `ocr/parsers.py` — Shared parsers with compiled regex patterns used by all OCR providers.
- `utils/auth.py` — API key validation (production only).
- `utils/rate_limiter.py` — Rate limiting by IP (10 req/min).
- `utils/upload_validator.py` — File validation (`UploadValidator` class).
- `config/common.py` — `PROJECT_ROOT` (shared between settings and server).
- `config/settings.py` — Domain config (OCR provider, upload validation, logging). Singleton: `settings`.
- `config/server.py` — Infrastructure config (env, workers, DB URL, storage, CORS). Singleton: `server_config`.
- `utils/exceptions.py` — `OCRError`, `StorageError`, `UploadValidationError` (each carries `mensaje`, `causa`, and provider/backend name).

**Config resolution order:** system env vars → `.env` file (via `python-dotenv`, `override=False`) → hardcoded defaults in dataclass.

**Request flow for `POST /api/upload`:**
`main.py` validates upload + sanitizes filename → streaming upload (8KB chunks to disk) → `service.guardar_imagen_fisica()` saves via storage backend → `service.procesar_y_guardar_comprobante()` runs OCR engine, persists `Comprobante` to DB → `ComprobanteResponse` dataclass → JSON response with extracted fields.

**Security features:**
- API key authentication via `X-Api-Key` header (production only)
- Rate limiting by IP (10 req/min on `/api/upload`)
- CSP headers (Content-Security-Policy, X-Content-Type-Options, X-Frame-Options)
- CORS configurable (warning if `*` in production)
- Secrets masked in logs and `__repr__`
- Docker USER no-root, healthcheck, .dockerignore

## How to Extend

**New OCR provider:** Inherit `OCRProvider` from `ocr/base.py`, implement `nombre` property + `extraer_campos(ruta) → OCRResult`, register via `registrar_ocr()` in `ocr/__init__.py`, add env vars to `.env`.

**New storage backend:** Inherit `StorageProvider` from `storage/base.py`, implement `nombre` property + `guardar(bytes, nombre) → str` + `resolver_ruta(ruta) → str` + `limpiar_temporal(ruta)`, register via `registrar_storage()` in `storage/__init__.py`.

**New DB engine:** Create `database/backends/new_engine.py` with engine factory function, register URL prefix in `database/engine.py::create_engine_from_url()`. No changes needed to models, service, or main.

**New ORM model:** Add to `database/models.py` inheriting `Base`. Optionally re-export from `database/__init__.py`.

## Key Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `ENV` | `development` or `production` | `development` |
| `PORT` | Server port | `8000` |
| `HOST` | Server host | `127.0.0.1` (dev) / `0.0.0.0` (prod) |
| `OCR_PROVIDER` | `gemini`, `tesseract`, or `ocrspace` | `ocrspace` |
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///./comprobantes.db` |
| `STORAGE_BACKEND` | `local`, `s3`, or `cloudinary` | `local` |
| `SAMI_API_KEY` | API key for authentication (production) | - |
| `GEMINI_API_KEY` | Google Gemini API key | - |
| `OCRSPACE_API_KEY` | OCR.space API key | - |

Production (`ENV=production`) auto-configures: 4 workers, no reload, `warning` log level, auth required. Dev uses 1 worker, hot-reload, `info` log level, auth skipped. See `.env.example` for the full reference.

## Optional Dependencies

`pyproject.toml` defines extras that are not installed by default:
- `s3` — `boto3` for S3/Backblaze B2/MinIO storage
- `postgres` — `psycopg2-binary` for PostgreSQL
- `cloudinary` — Cloudinary storage
- `dev` — `pytest`, `httpx` for testing
- `all` — installs everything

## Known Debt (from BACKLOG.md)

- PWA Service Worker is a skeleton with no offline caching
- B6: `os.path.exists()` per request in Tesseract (~1ms overhead)
- B7: PostgreSQL config incomplete (missing `max_overflow`, `pool_timeout`)
- B8: IO disk per log entry (mitigated by buffered handler)
