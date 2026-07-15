# AGENTS.md — Guidance for AI agents working in SAMI

## Language rule (critical)

All code, comments, docstrings, and documentation in this repo are in Spanish. Match this when writing new code. English variable names are fine (they're already used), but every comment, docstring, and user-facing string must be in Spanish.

## Commands

```bash
uv sync                     # Install base deps
uv sync --all-extras        # Install everything (needed for tests)
python run.py               # Dev server (hot-reload, port 8000)
uv run pytest               # All tests
uv run pytest tests/test_upload_validator.py::TestValidarClienteId::test_id_valido_tienda_001  # Single test
uv run ruff check .         # Lint (uses ruff defaults — no config file)
uv run ruff format .        # Format
```

No CI, no pre-commit hooks, no ruff.toml, no pytest.ini. Ruff and pytest run with defaults.

## Architecture (3 layers + two strategy modules)

```
run.py → boots uvicorn with main:app
  ├─ main.py      — routes, CORS, static mount
  ├─ service.py   — business logic (NO direct OCR/storage code)
  └─ database/    — SQLAlchemy ORM, engine factory, sessions
       └─ backends/ — sqlite.py, postgres.py (add new engines here)
```

**Strategy modules:**
- `ocr/` — `OCRProvider` ABC + 3 providers (gemini, tesseract, ocrspace) + `FallbackProvider` decorator. Factory: `get_ocr_engine()`.
- `storage/` — `StorageProvider` ABC + 3 backends (local, s3, cloudinary). Factory: `get_storage_backend()`.

**Two config singletons** — don't confuse them:
- `config/settings.py` → domain config (OCR provider, upload limits, logging). Singleton: `settings`.
- `config/server.py` → infrastructure config (env, port, DB URL, storage, CORS). Singleton: `server_config`.

Both load `.env` via `python-dotenv` with `override=False` — system env vars always win.

## Key gotchas

- **`.env` has `override=False`**: if a variable exists in the system environment, the `.env` file value is ignored. This is intentional.
- **`comprobantes.db`** in the repo root is the SQLite database. It's auto-created by `database/models.py` via `Base.metadata.create_all()` at import time.
- **OCR blocks the event loop**: `engine.extraer_campos()` runs synchronously inside an async FastAPI handler. Known issue (see BACKLOG.md item 4). Don't make it worse by adding more sync blocking calls.
- **`monto` and `destinatario` are NOT persisted**: OCR extracts them but `database/models.py` has no columns for them. The API response attaches them via `_monto`/`_destinatario` attributes (not DB columns).
- **Remote storage temp files leak on OCR error**: when `STORAGE_BACKEND` is s3/cloudinary and OCR fails, the downloaded temp file isn't cleaned up. `_limpiar_temporal()` only runs on the happy path.
- **Regex not compiled**: `_parsear_campos()` in tesseract and ocrspace providers recompiles ~15 patterns per call. Known issue.
- **Duplicated regex**: `tesseract_provider.py` and `ocrspace_provider.py` share ~80 lines of nearly identical regex parsing. Should be in `ocr/parsers.py` but isn't yet.

## How to extend

- **New OCR provider**: inherit `OCRProvider` from `ocr/base.py`, implement `nombre` + `extraer_campos()`, register in `ocr/__init__.py::get_ocr_engine()`.
- **New storage backend**: inherit `StorageProvider` from `storage/base.py`, implement `nombre` + `guardar()`, register in `storage/__init__.py::get_storage_backend()`.
- **New DB engine**: create `database/backends/new_engine.py`, register URL prefix in `database/engine.py::create_engine_from_url()`.

## Testing

- Only `test_upload_validator.py` exists. Uses `pytest` + `httpx` (the `dev` extra).
- Tests call `configure()` before each validation to set limits — this is required because the validator uses module-level state.
- `PIL` is used in tests to create in-memory test images.

## Deployment

- `Procfile`: `web: uv run python run.py`
- `Dockerfile`: Python 3.11-slim + tesseract-ocr-spa + uv
- `docker-compose.yml`: app + PostgreSQL 16, port 7000
- Production auto-configures: 4 workers, no reload, `warning` log level

## Known debt

See `BACKLOG.md` for the full list. Don't fix things outside your scope — the backlog items are numbered and tracked.
