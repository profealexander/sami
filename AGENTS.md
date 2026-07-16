# AGENTS.md — Guidance for AI agents working in SAMIOCR

## Language rule (critical)

All code, comments, docstrings, and documentation in this repo are in Spanish. Match this when writing new code. English variable names are fine (they're already used), but every comment, docstring, and user-facing string must be in Spanish.

## Commands

```bash
uv sync                     # Install base deps
uv sync --all-extras        # Install everything (needed for tests)
python run.py               # Dev server (hot-reload, port 8000)
uv run pytest               # All tests (32 tests)
uv run pytest tests/test_upload_validator.py::TestValidarClienteId::test_id_valido_tienda_001  # Single test
uv run ruff check .         # Lint (uses ruff defaults — no config file)
uv run ruff format .        # Format
```

No CI, no pre-commit hooks, no ruff.toml, no pytest.ini. Ruff and pytest run with defaults.

## Architecture (3 layers + strategy modules + utils)

```
run.py → boots uvicorn with main:app
  ├─ main.py      — routes, CORS, CSP headers, static mount, startup event
  ├─ service.py   — business logic (ComprobanteResponse, no monkey-patching)
  └─ database/    — SQLAlchemy ORM, engine factory, sessions
       └─ backends/ — sqlite.py, postgres.py (add new engines here)

Utils:
  ├─ utils/auth.py         — API key validation
  ├─ utils/rate_limiter.py — Rate limiting by IP
  ├─ utils/upload_validator.py — File validation (UploadValidator class)
  └─ utils/exceptions.py   — Custom exceptions

Config:
  ├─ config/common.py      — PROJECT_ROOT (shared)
  ├─ config/settings.py    — Domain config (OCR, uploads, logging)
  ├─ config/server.py      — Infrastructure config (env, DB, storage, CORS)
  └─ config/logger.py      — Logging with daily rotation
```

**Strategy modules:**
- `ocr/` — `OCRProvider` ABC + 3 providers (gemini, tesseract, ocrspace) + `FallbackProvider` with circuit breaker. Factory: `get_ocr_engine()`.
- `storage/` — `StorageProvider` ABC + 3 backends (local, s3, cloudinary) with `resolver_ruta()` and `limpiar_temporal()`. Factory: `get_storage_backend()`.

**Config singletons:**
- `config/settings.py` → domain config (OCR provider, upload limits, logging). Singleton: `settings`.
- `config/server.py` → infrastructure config (env, port, DB URL, storage, CORS). Singleton: `server_config`.

Both load `.env` via `python-dotenv` with `override=False` — system env vars always win.

## Key features

- **Streaming upload**: Images are written to disk in 8KB chunks, not loaded entirely into RAM
- **Circuit breaker**: FallbackProvider disables primary after 5 consecutive failures for 60s
- **Singleton clients**: Gemini and S3 clients are reused across requests
- **Shared parsers**: `ocr/parsers.py` contains compiled regex patterns used by all providers
- **ComprobanteResponse**: Dataclass separating API response from ORM model (no monkey-patching)
- **Health check**: GET /health verifies database connection
- **Auth + Rate limiting**: API key required in production, 10 req/min per IP

## Key gotchas

- **`.env` has `override=False`**: if a variable exists in the system environment, the `.env` file value is ignored. This is intentional.
- **`comprobantes.db`** is auto-created on startup via `@app.on_event("startup")` in main.py, NOT at import time.
- **Auth only in production**: In development, API key validation is skipped. Rate limiting still applies.
- **Rate limiter is in-memory**: Resets on server restart. Not persistent across restarts.
- **SQLite in production**: Works but limited. Use PostgreSQL for production with multiple workers.

## How to extend

- **New OCR provider**: inherit `OCRProvider` from `ocr/base.py`, implement `nombre` + `extraer_campos()`, register via `registrar_ocr()` in `ocr/__init__.py`.
- **New storage backend**: inherit `StorageProvider` from `storage/base.py`, implement `nombre` + `guardar()` + `resolver_ruta()` + `limpiar_temporal()`, register via `registrar_storage()` in `storage/__init__.py`.
- **New DB engine**: create `database/backends/new_engine.py`, register URL prefix in `database/engine.py::create_engine_from_url()`.

## Testing

4 test files, 32 tests:
- `test_upload_validator.py` — File validation (15 tests)
- `test_auth.py` — API key auth (4 tests)
- `test_rate_limiter.py` — Rate limiting (4 tests)
- `test_parsers.py` — OCR parsers (9 tests)

Tests use `pytest` + `httpx` (the `dev` extra).
`PIL` is used in tests to create in-memory test images.

## Deployment

- `Procfile`: `web: uv run python run.py`
- `Dockerfile`: Python 3.11-slim + tesseract-ocr-spa + uv + curl (USER no-root, HEALTHCHECK)
- `docker-compose.yml`: app + PostgreSQL 16, port 8000, healthcheck, POSTGRES_PASSWORD from .env
- `.dockerignore`: Excludes .git, __pycache__, .env, tests/, docs/, logs/, uploads/
- Production auto-configures: 4 workers, no reload, `warning` log level

## Known debt

See `BACKLOG.md` for the full list. 3 minor items remain (B6: os.path.exists per request, B7: PG config incomplete, B8: IO disk per log).
