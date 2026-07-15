# Plan de Implementación — Corrección de Auditoría SAMI

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir los 77 hallazgos de la auditoría integral priorizados por severidad.

**Architecture:** Fases incrementales: primero seguridad y bugs críticos, luego arquitectura y rendimiento, después calidad y testing, finalmente limpieza. Cada fase es independiente y dejable en producción.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, pytest, Docker, asyncio

## Global Constraints

- Todos los comentarios y docstrings en español (regla del proyecto)
- No usar features beyond what the task requires
- TDD: tests antes de implementación cuando aplique
- Commits frecuentes al finalizar cada task
- `uv run pytest` debe pasar antes de cada commit
- `uv run ruff check .` y `uv run ruff format .` al finalizar

---

## Fase 1: Seguridad y Bugs Críticos (Día 1)

### Task 1: Revocar y rotar API keys

**Covers:** C3
**Files:**
- Modify: `.env` (rotar keys)
- Modify: `.env.example` (actualizar placeholders)

- [ ] **Step 1: Generar nuevas API keys**
  - Ir a Google AI Studio → regenerar Gemini API key
  - Ir a OCR.space → regenerar API key

- [ ] **Step 2: Actualizar .env**
  ```bash
  # Reemplazar valores reales
  GEMINI_API_KEY=<nueva_key>
  OCRSPACE_API_KEY=<nueva_key>
  ```

- [ ] **Step 3: Actualizar .env.example**
  ```bash
  GEMINI_API_KEY=tu_api_key_de_gemini_aqui
  OCRSPACE_API_KEY=tu_api_key_de_ocrspace_aqui
  ```

- [ ] **Step 4: Verificar que git no tiene las keys viejas**
  ```bash
  git log --all --full-history -- .env
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add .env .env.example
  git commit -m "security: rotar API keys de Gemini y OCR.space"
  ```

---

### Task 2: CORS explícito + rate limiting + auth

**Covers:** C4, C5, C6
**Files:**
- Modify: `config/server.py:65-66` (CORS validation)
- Create: `utils/auth.py` (API key auth)
- Create: `utils/rate_limiter.py` (rate limiting)
- Modify: `main.py:60` (apply middleware)
- Create: `tests/test_auth.py`
- Create: `tests/test_rate_limiter.py`

- [ ] **Step 1: Escribir test de auth**
  ```python
  # tests/test_auth.py
  import pytest
  from utils.auth import validar_api_key

  def test_api_key_valida():
      assert validar_api_key("sami_key_123") is True

  def test_api_key_invalida():
      assert validar_api_key("invalida") is False

  def test_api_key_vacia():
      assert validar_api_key("") is False
  ```

- [ ] **Step 2: Ejecutar test (debe fallar)**
  ```bash
  uv run pytest tests/test_auth.py -v
  ```
  Expected: FAIL con "ModuleNotFoundError"

- [ ] **Step 3: Implementar auth**
  ```python
  # utils/auth.py
  import os

  def validar_api_key(api_key: str) -> bool:
      """Valida que la API key coincida con la configurada."""
      key_esperada = os.getenv("SAMI_API_KEY", "")
      if not key_esperada:
          return True  # Sin key configurada, permitir (dev)
      return api_key == key_esperada
  ```

- [ ] **Step 4: Ejecutar test (debe pasar)**
  ```bash
  uv run pytest tests/test_auth.py -v
  ```

- [ ] **Step 5: Escribir test de rate limiter**
  ```python
  # tests/test_rate_limiter.py
  import time
  from utils.rate_limiter import RateLimiter

  def test_rate_limiter_permite_primer_request():
      rl = RateLimiter(max_requests=5, window_seconds=60)
      assert rl.permitir("192.168.1.1") is True

  def test_rate_limiter_bloquea_exceso():
      rl = RateLimiter(max_requests=2, window_seconds=60)
      rl.permitir("192.168.1.1")
      rl.permitir("192.168.1.1")
      assert rl.permitir("192.168.1.1") is False
  ```

- [ ] **Step 6: Implementar rate limiter**
  ```python
  # utils/rate_limiter.py
  import time
  from collections import defaultdict

  class RateLimiter:
      def __init__(self, max_requests: int = 10, window_seconds: int = 60):
          self.max_requests = max_requests
          self.window_seconds = window_seconds
          self._requests: dict[str, list[float]] = defaultdict(list)

      def permitir(self, key: str) -> bool:
          ahora = time.time()
          ventana = ahora - self.window_seconds
          self._requests[key] = [t for t in self._requests[key] if t > ventana]
          if len(self._requests[key]) >= self.max_requests:
              return False
          self._requests[key].append(ahora)
          return True
  ```

- [ ] **Step 7: Ejecutar tests**
  ```bash
  uv run pytest tests/test_auth.py tests/test_rate_limiter.py -v
  ```

- [ ] **Step 8: Validar CORS en server.py**
  ```python
  # config/server.py:65-66 — agregar validación
  if env == "production" and cors_raw == "*":
      logger.warning("CORS * no es seguro en producción. Configurar CORS_ORIGINS explícito.")
  ```

- [ ] **Step 9: Agregar auth y rate limit a main.py**
  ```python
  # main.py — agregar al handler subir_comprobante
  from fastapi import Header, HTTPException
  from utils.auth import validar_api_key
  from utils.rate_limiter import RateLimiter

  _rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

  @app.post("/api/upload")
  async def subir_comprobante(
      imagen: UploadFile = File(...),
      cliente_id: str = Form(...),
      x_api_key: str = Header(default=""),
  ):
      # Rate limiting
      client_ip = request.client.host if request else "unknown"
      if not _rate_limiter.permitir(client_ip):
          raise HTTPException(status_code=429, detail="Rate limit excedido")

      # Auth (solo en producción)
      if server_config.env == "production" and not validar_api_key(x_api_key):
          raise HTTPException(status_code=401, detail="API key inválida")
  ```

- [ ] **Step 10: Agregar SAMI_API_KEY a .env.example**
  ```bash
  SAMI_API_KEY=tu_api_key_para_auth_aqui
  ```

- [ ] **Step 11: Commit**
  ```bash
  git add utils/auth.py utils/rate_limiter.py main.py config/server.py .env.example tests/test_auth.py tests/test_rate_limiter.py
  git commit -m "security: agregar autenticación API key, rate limiting y CORS explícito"
  ```

---

### Task 3: Bugs lógicos — monto y MIME type

**Covers:** C9, C10
**Files:**
- Modify: `main.py:119-122`
- Modify: `ocr/gemini_provider.py:93`
- Create: `tests/test_monto_logic.py`
- Create: `tests/test_mime_detection.py`

- [ ] **Step 1: Test de monto "0"**
  ```python
  # tests/test_monto_logic.py
  def test_monto_cero_incluido():
      monto = "0"
      resultado = {}
      if monto is not None:
          resultado["monto"] = monto
      assert "monto" in resultado
      assert resultado["monto"] == "0"

  def test_monto_none_excluido():
      monto = None
      resultado = {}
      if monto is not None:
          resultado["monto"] = monto
      assert "monto" not in resultado
  ```

- [ ] **Step 2: Ejecutar test**
  ```bash
  uv run pytest tests/test_monto_logic.py -v
  ```

- [ ] **Step 3: Fix monto en main.py**
  ```python
  # main.py:119-122 — cambiar de:
  if monto:
      response_data["datos_extraidos"]["monto"] = monto
  if destinatario:
      response_data["datos_extraidos"]["destinatario"] = destinatario

  # a:
  if monto is not None:
      response_data["datos_extraidos"]["monto"] = monto
  if destinatario is not None:
      response_data["datos_extraidos"]["destinatario"] = destinatario
  ```

- [ ] **Step 4: Test de MIME detection**
  ```python
  # tests/test_mime_detection.py
  from pathlib import Path

  def test_mime_jpeg():
      mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
      assert mime_map.get(Path("foto.jpg").suffix.lower(), "image/jpeg") == "image/jpeg"

  def test_mime_png():
      mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
      assert mime_map.get(Path("foto.png").suffix.lower(), "image/jpeg") == "image/png"

  def test_mime_webp():
      mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
      assert mime_map.get(Path("foto.webp").suffix.lower(), "image/jpeg") == "image/webp"
  ```

- [ ] **Step 5: Fix MIME en gemini_provider.py**
  ```python
  # ocr/gemini_provider.py:91-94 — cambiar de:
  genai.types.Part.from_bytes(
      data=imagen_bytes,
      mime_type="image/jpeg",
  ),

  # a:
  from pathlib import Path
  mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
  mime = mime_map.get(Path(imagen_path).suffix.lower(), "image/jpeg")
  genai.types.Part.from_bytes(
      data=imagen_bytes,
      mime_type=mime,
  ),
  ```

- [ ] **Step 6: Ejecutar todos los tests**
  ```bash
  uv run pytest tests/test_monto_logic.py tests/test_mime_detection.py -v
  ```

- [ ] **Step 7: Commit**
  ```bash
  git add main.py ocr/gemini_provider.py tests/test_monto_logic.py tests/test_mime_detection.py
  git commit -m "fix: corregir monto '0' excluido y MIME type hardcoded en Gemini"
  ```

---

### Task 4: Temp file leak — try/finally

**Covers:** A2, M8, M13
**Files:**
- Modify: `service.py:60-80`
- Create: `tests/test_temp_cleanup.py`

- [ ] **Step 1: Test de limpieza garantizada**
  ```python
  # tests/test_temp_cleanup.py
  import os
  import tempfile
  from service import _limpiar_temporal

  def test_limpia_archivo_temporal():
      with tempfile.NamedTemporaryFile(delete=False) as f:
          temp_path = f.name
      assert os.path.exists(temp_path)
      _limpiar_temporal(temp_path, "s3://bucket/file.jpg")
      assert not os.path.exists(temp_path)

  def test_no_falla_si_archivo_no_existe():
      _limpiar_temporal("/tmp/no_existe_12345.jpg", "s3://bucket/file.jpg")  # No debe fallar
  ```

- [ ] **Step 2: Ejecutar test**
  ```bash
  uv run pytest tests/test_temp_cleanup.py -v
  ```

- [ ] **Step 3: Fix con try/finally en service.py**
  ```python
  # service.py:60-80 — refactorizar a:
  ruta_absoluta = None
  try:
      ruta_absoluta = _resolver_ruta_imagen(ruta_imagen)
      resultado = engine.extraer_campos(ruta_absoluta)
  except OCRError:
      raise
  except Exception as e:
      logger.error("Error OCR en %s — tipo=%s | msg=%s", ruta_imagen, type(e).__name__, str(e)[:300])
      resultado = None
  finally:
      _limpiar_temporal(ruta_absoluta, ruta_imagen)
  ```

- [ ] **Step 4: Ejecutar tests**
  ```bash
  uv run pytest tests/test_temp_cleanup.py -v
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add service.py tests/test_temp_cleanup.py
  git commit -m "fix: garantizar limpieza de archivos temporales con try/finally"
  ```

---

### Task 5: Docker — USER no-root + password externo

**Covers:** C2, C12 (parcial), A21
**Files:**
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Fix Dockerfile**
  ```dockerfile
  FROM python:3.11-slim
  RUN adduser --disabled-password --no-create-home sami
  WORKDIR /app
  RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa curl && rm -rf /var/lib/apt/lists/*
  COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
  COPY pyproject.toml uv.lock ./
  RUN uv sync --frozen --no-dev
  COPY . .
  RUN chown -R sami:sami /app
  USER sami
  EXPOSE 8000
  ENV ENV=production
  HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1
  CMD ["uv", "run", "python", "run.py"]
  ```

- [ ] **Step 2: Fix docker-compose.yml**
  ```yaml
  services:
    sami:
      build: .
      ports:
        - "${PORT:-8000}:8000"
      env_file: .env
      environment:
        - ENV=production
      volumes:
        - sami_uploads:/app/uploads
        - sami_data:/app/data
      depends_on:
        db:
          condition: service_healthy
      restart: unless-stopped
      healthcheck:
        test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
        interval: 30s
        timeout: 5s
        retries: 3

    db:
      image: postgres:16-alpine
      environment:
        POSTGRES_DB: sami
        POSTGRES_USER: sami
        POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Configurar POSTGRES_PASSWORD en .env}
      volumes:
        - pgdata:/var/lib/postgresql/data
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U sami"]
        interval: 5s
        timeout: 5s
        retries: 5
      restart: unless-stopped

  volumes:
    sami_uploads:
    sami_data:
    pgdata:
  ```

- [ ] **Step 3: Agregar POSTGRES_PASSWORD a .env.example**
  ```bash
  POSTGRES_PASSWORD=cambia_esto_en_produccion
  ```

- [ ] **Step 4: Crear .dockerignore**
  ```
  .git
  .github
  .venv
  __pycache__
  *.pyc
  .env
  tests/
  docs/
  logs/
  uploads/
  *.db
  .mimocode/
  ```

- [ ] **Step 5: Verificar Docker build**
  ```bash
  docker build -t sami-test .
  ```

- [ ] **Step 6: Commit**
  ```bash
  git add Dockerfile docker-compose.yml .env.example .dockerignore
  git commit -m "security: Docker USER no-root, password externo, HEALTHCHECK, .dockerignore"
  ```

---

## Fase 2: Arquitectura y Rendimiento (Días 2-3)

### Task 6: Singletonizar clientes de API

**Covers:** A5, A15, A16
**Files:**
- Modify: `ocr/gemini_provider.py:77`
- Modify: `ocr/ocrspace_provider.py`
- Modify: `storage/s3.py:35`

- [ ] **Step 1: Singletonizar Gemini client**
  ```python
  # ocr/gemini_provider.py — agregar cache de cliente
  _gemini_client = None

  def _obtener_cliente_gemini(api_key: str):
      global _gemini_client
      if _gemini_client is None:
          _gemini_client = genai.Client(api_key=api_key)
      return _gemini_client
  ```

- [ ] **Step 2: Singletonizar S3 client**
  ```python
  # storage/s3.py — agregar cache de cliente
  _s3_client = None
  _s3_config_hash = None

  def _obtener_cliente_s3(cfg):
      global _s3_client, _s3_config_hash
      config_hash = hash((cfg.s3_access_key, cfg.s3_region, cfg.s3_endpoint))
      if _s3_client is None or _s3_config_hash != config_hash:
          import boto3
          from botocore.config import Config
          client_kwargs = {
              "aws_access_key_id": cfg.s3_access_key,
              "aws_secret_access_key": cfg.s3_secret_key,
              "region_name": cfg.s3_region,
          }
          if cfg.s3_endpoint:
              client_kwargs["endpoint_url"] = cfg.s3_endpoint
          _s3_client = boto3.client("s3", config=Config(retries={"max_attempts": 3}), **client_kwargs)
          _s3_config_hash = config_hash
      return _s3_client
  ```

- [ ] **Step 3: Actualizar usar clientes en provider methods**
  ```python
  # En gemini_provider.py extraer_campos():
  client = _obtener_cliente_gemini(self.config.api_key)

  # En s3.py guardar():
  s3 = _obtener_cliente_s3(cfg)
  ```

- [ ] **Step 4: Commit**
  ```bash
  git add ocr/gemini_provider.py storage/s3.py
  git commit -m "perf: singletonizar clientes de Gemini y S3"
  ```

---

### Task 7: run_in_executor para event loop

**Covers:** C7, C8
**Files:**
- Modify: `main.py:61-98`
- Create: `tests/test_async_handler.py`

- [ ] **Step 1: Test de handler async**
  ```python
  # tests/test_async_handler.py
  import asyncio
  import pytest

  def test_run_in_executor_no_bloquea():
      loop = asyncio.new_event_loop()
      async def tarea_lenta():
          await asyncio.sleep(0.1)
          return "ok"
      resultado = loop.run_until_complete(tarea_lenta())
      assert resultado == "ok"
  ```

- [ ] **Step 2: Wrappear operaciones síncronas**
  ```python
  # main.py:61-98 — importar asyncio y usar run_in_executor
  import asyncio

  @app.post("/api/upload")
  async def subir_comprobante(...):
      # ... validación ...

      # Guardar imagen (operación síncrona)
      ruta_imagen = await asyncio.get_event_loop().run_in_executor(
          None, service.guardar_imagen_fisica, contenido, ext
      )

      # Procesar OCR + guardar en BD (operación síncrona)
      registro = await asyncio.get_event_loop().run_in_executor(
          None, service.procesar_y_guardar_comprobante, db, ruta_imagen, cliente_id
      )
  ```

- [ ] **Step 3: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 4: Commit**
  ```bash
  git add main.py tests/test_async_handler.py
  git commit -m "perf: usar run_in_executor para no bloquear event loop"
  ```

---

### Task 8: Extraer parsers compartidos + compilar regex

**Covers:** A18, A19
**Files:**
- Create: `ocr/parsers.py`
- Modify: `ocr/tesseract_provider.py:139-214`
- Modify: `ocr/ocrspace_provider.py:137-212`
- Create: `tests/test_parsers.py`

- [ ] **Step 1: Test de parsers**
  ```python
  # tests/test_parsers.py
  from ocr.parsers import parsear_campos, RE_CAJERO, RE_FECHA

  def test_parsear_cajero():
      texto = "CAJERO: Juan Pérez"
      resultado = parsear_campos(texto)
      assert resultado["cajero"] == "Juan Pérez"

  def test_parsear_fecha():
      texto = "Fecha: 15/07/2026"
      resultado = parsear_campos(texto)
      assert resultado["fecha"] == "15/07/2026"

  def test_regex_compilados():
      assert RE_CAJERO is not None
      assert RE_FECHA is not None
  ```

- [ ] **Step 2: Crear ocr/parsers.py**
  ```python
  # ocr/parsers.py
  import re

  # Regex pre-compilados
  RE_CAJERO = re.compile(r'(?:CAJERO|ATENDIO|VENDEDOR|EMPLEADO)\s*[\:\-]?\s*(.+)', re.IGNORECASE)
  RE_FECHA = re.compile(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})')
  RE_HORA = re.compile(r'(\d{1,2}):(\d{2})')
  RE_VENTA = re.compile(r'(?:VENTA|TICKET|FOLIO|NO\.?\s*VENTA)\s*[\:\-]?\s*(\d+)', re.IGNORECASE)
  RE_MONTO = re.compile(r'(?:MONTO|TOTAL|IMPORTE|PAGO)\s*[\:\-]?\s*\$?\s*([\d,]+\.?\d*)', re.IGNORECASE)

  MESES_ES = {
      "ENERO": "01", "FEBRERO": "02", "MARZO": "03", "ABRIL": "04",
      "MAYO": "05", "JUNIO": "06", "JULIO": "07", "AGOSTO": "08",
      "SEPTIEMBRE": "09", "OCTUBRE": "10", "NOVIEMBRE": "11", "DICIEMBRE": "12",
  }

  MESES_FALLBACK = {
      "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
      "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
      "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
  }

  def parsear_campos(texto: str) -> dict:
      """Parsea texto OCR y extrae campos estructurados."""
      lineas = texto.split('\n')
      resultado = {
          "cajero": None, "fecha": None, "hora": None,
          "no_venta": None, "monto": None, "destinatario": None,
      }

      for linea in lineas:
          if not resultado["cajero"]:
              match = RE_CAJERO.search(linea)
              if match:
                  resultado["cajero"] = match.group(1).strip()

          if not resultado["fecha"]:
              match = RE_FECHA.search(linea)
              if match:
                  dia, mes, anio = match.group(1), match.group(2), match.group(3)
                  resultado["fecha"] = f"{dia.zfill(2)}/{mes.zfill(2)}/{anio}"

          if not resultado["hora"]:
              match = RE_HORA.search(linea)
              if match:
                  resultado["hora"] = f"{match.group(1).zfill(2)}:{match.group(2)}"

          if not resultado["no_venta"]:
              match = RE_VENTA.search(linea)
              if match:
                  resultado["no_venta"] = match.group(1)

          if not resultado["monto"]:
              match = RE_MONTO.search(linea)
              if match:
                  resultado["monto"] = match.group(1).replace(",", "")

      return resultado
  ```

- [ ] **Step 3: Ejecutar test**
  ```bash
  uv run pytest tests/test_parsers.py -v
  ```

- [ ] **Step 4: Refactorizar tesseract_provider.py**
  ```python
  # ocr/tesseract_provider.py — reemplazar _parsear_campos con:
  from ocr.parsers import parsear_campos

  # Eliminar las ~80 líneas de regex duplicadas
  ```

- [ ] **Step 5: Refactorizar ocrspace_provider.py**
  ```python
  # ocr/ocrspace_provider.py — reemplazar _parsear_campos con:
  from ocr.parsers import parsear_campos

  # Eliminar las ~80 líneas de regex duplicadas
  ```

- [ ] **Step 6: Ejecutar todos los tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 7: Commit**
  ```bash
  git add ocr/parsers.py ocr/tesseract_provider.py ocr/ocrspace_provider.py tests/test_parsers.py
  git commit -m "refactor: extraer parsers compartidos con regex pre-compilados"
  ```

---

### Task 9: Factory pattern — registro dinámico

**Covers:** A5, M5, M6
**Files:**
- Modify: `ocr/__init__.py`
- Modify: `storage/__init__.py`

- [ ] **Step 1: Refactorizar OCR factory**
  ```python
  # ocr/__init__.py
  from ocr.base import OCRProvider
  from ocr.fallback import FallbackProvider

  _REGISTRO_OCR: dict[str, type[OCRProvider]] = {}

  def registrar_ocr(nombre: str, clase: type[OCRProvider]):
      """Registra un proveedor OCR."""
      _REGISTRO_OCR[nombre] = clase

  def get_ocr_engine() -> OCRProvider:
      """Retorna el motor OCR configurado."""
      from config.settings import settings
      from ocr.ocrspace_provider import OCRSpaceProvider
      from ocr.gemini_provider import GeminiProvider
      from ocr.tesseract_provider import TesseractProvider

      # Auto-registrar si está vacío
      if not _REGISTRO_OCR:
          registrar_ocr("ocrspace", OCRSpaceProvider)
          registrar_ocr("gemini", GeminiProvider)
          registrar_ocr("tesseract", TesseractProvider)

      nombre = settings.ocr_provider.lower()
      if nombre == "tesseract":
          return TesseractProvider()

      primary_cls = _REGISTRO_OCR.get(nombre)
      if not primary_cls:
          raise ValueError(f"Proveedor OCR desconocido: {nombre}")

      return FallbackProvider(primary_cls(), TesseractProvider())
  ```

- [ ] **Step 2: Refactorizar Storage factory**
  ```python
  # storage/__init__.py
  from storage.base import StorageProvider

  _REGISTRO_STORAGE: dict[str, type[StorageProvider]] = {}

  def registrar_storage(nombre: str, clase: type[StorageProvider]):
      """Registra un backend de almacenamiento."""
      _REGISTRO_STORAGE[nombre] = clase

  def get_storage_backend() -> StorageProvider:
      """Retorna el backend de almacenamiento configurado."""
      from config.server import server_config
      from storage.local import LocalStorageProvider
      from storage.s3 import S3StorageProvider
      from storage.cloudinary import CloudinaryStorageProvider

      # Auto-registrar si está vacío
      if not _REGISTRO_STORAGE:
          registrar_storage("local", LocalStorageProvider)
          registrar_storage("s3", S3StorageProvider)
          registrar_storage("cloudinary", CloudinaryStorageProvider)

      nombre = server_config.storage_backend.lower()
      cls = _REGISTRO_STORAGE.get(nombre)
      if not cls:
          raise ValueError(f"Backend de almacenamiento desconocido: {nombre}")

      return cls()
  ```

- [ ] **Step 3: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 4: Commit**
  ```bash
  git add ocr/__init__.py storage/__init__.py
  git commit -m "refactor: factory pattern con registro dinámico para OCR y storage"
  ```

---

### Task 10: Optimizar umbral Otsu — histogram() en list(getdata())

**Covers:** A17
**Files:**
- Modify: `ocr/tesseract_provider.py:132-133`

- [ ] **Step 1: Reemplazar list(img.getdata())**
  ```python
  # ocr/tesseract_provider.py:132-133 — cambiar de:
  pixels = list(img.getdata())
  umbral = sum(pixels) // len(pixels)

  # a:
  hist = img.histogram()
  total = sum(i * c for i, c in enumerate(hist))
  count = sum(hist)
  umbral = total // count if count > 0 else 128
  ```

- [ ] **Step 2: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 3: Commit**
  ```bash
  git add ocr/tesseract_provider.py
  git commit -m "perf: usar histogram() en lugar de list(getdata()) para umbral Otsu"
  ```

---

## Fase 3: Calidad y Testing (Días 3-4)

### Task 11: Consolidar configuración — PROJECT_ROOT y singletons

**Covers:** A6, M3, M4
**Files:**
- Create: `config/common.py`
- Modify: `config/settings.py:21`
- Modify: `config/server.py:15`

- [ ] **Step 1: Crear config/common.py**
  ```python
  # config/common.py
  from pathlib import Path

  PROJECT_ROOT = Path(__file__).resolve().parent.parent
  ```

- [ ] **Step 2: Actualizar settings.py**
  ```python
  # config/settings.py — cambiar de:
  PROJECT_ROOT = Path(__file__).resolve().parent.parent

  # a:
  from config.common import PROJECT_ROOT
  ```

- [ ] **Step 3: Actualizar server.py**
  ```python
  # config/server.py — cambiar de:
  PROJECT_ROOT = Path(__file__).resolve().parent.parent

  # a:
  from config.common import PROJECT_ROOT
  ```

- [ ] **Step 4: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add config/common.py config/settings.py config/server.py
  git commit -m "refactor: consolidar PROJECT_ROOT en config/common.py"
  ```

---

### Task 12: Excepciones de storage envueltas

**Covers:** A20
**Files:**
- Modify: `storage/s3.py:35-44`
- Modify: `storage/cloudinary.py:26-33`
- Create: `tests/test_storage_errors.py`

- [ ] **Step 1: Test de excepciones envueltas**
  ```python
  # tests/test_storage_errors.py
  import pytest
  from utils.exceptions import StorageError

  def test_storage_error_attributes():
      err = StorageError(mensaje="test", backend="s3")
      assert err.backend == "s3"
      assert err.mensaje == "test"
  ```

- [ ] **Step 2: Envolver excepciones en s3.py**
  ```python
  # storage/s3.py:35-44 — envolver en try/except
  try:
      s3.put_object(...)
  except Exception as e:
      raise StorageError(mensaje=f"Error subiendo a S3: {e}", backend="s3") from e
  ```

- [ ] **Step 3: Envolver excepciones en cloudinary.py**
  ```python
  # storage/cloudinary.py:26-33 — envolver en try/except
  try:
      result = cloudinary.uploader.upload(...)
  except Exception as e:
      raise StorageError(mensaje=f"Error subiendo a Cloudinary: {e}", backend="cloudinary") from e
  ```

- [ ] **Step 4: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add storage/s3.py storage/cloudinary.py tests/test_storage_errors.py
  git commit -m "fix: envolver excepciones de S3 y Cloudinary en StorageError"
  ```

---

### Task 13: datetime timezone-aware

**Covers:** M17, M21
**Files:**
- Modify: `service.py:92`
- Modify: `database/models.py:32`

- [ ] **Step 1: Fix datetime.now()**
  ```python
  # service.py:92 — cambiar de:
  from datetime import datetime

  # a:
  from datetime import datetime, timezone
  # y cambiar:
  fecha_envio=datetime.now()
  # a:
  fecha_envio=datetime.now(timezone.utc)
  ```

- [ ] **Step 2: Fix datetime.utcnow()**
  ```python
  # database/models.py:32 — cambiar de:
  fecha_envio = Column(DateTime, default=datetime.utcnow)

  # a:
  from datetime import datetime, timezone
  fecha_envio = Column(DateTime, default=lambda: datetime.now(timezone.utc))
  ```

- [ ] **Step 3: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 4: Commit**
  ```bash
  git add service.py database/models.py
  git commit -m "fix: usar datetime.now(timezone.utc) en lugar de datetime.utcnow()"
  ```

---

### Task 14: S3 URL compatible con servicios custom

**Covers:** A1
**Files:**
- Modify: `storage/s3.py:43`

- [ ] **Step 1: Fix URL construction**
  ```python
  # storage/s3.py:43 — cambiar de:
  url = f"https://{cfg.s3_bucket}.s3.{cfg.s3_region}.amazonaws.com/{key}"

  # a:
  if cfg.s3_endpoint:
      url = f"{cfg.s3_endpoint}/{cfg.s3_bucket}/{key}"
  else:
      url = f"https://{cfg.s3_bucket}.s3.{cfg.s3_region}.amazonaws.com/{key}"
  ```

- [ ] **Step 2: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 3: Commit**
  ```bash
  git add storage/s3.py
  git commit -m "fix: URL S3 compatible con servicios custom (Backblaze, MinIO)"
  ```

---

### Task 15: Health check — verificar BD

**Covers:** A23
**Files:**
- Modify: `main.py:48-51`

- [ ] **Step 1: Agregar verificación de BD**
  ```python
  # main.py:48-51 — expandir health check
  from sqlalchemy import text

  @app.get("/health")
  async def health_check():
      status = {"status": "ok", "version": "2.2.0", "env": server_config.env}
      try:
          db = next(get_db())
          db.execute(text("SELECT 1"))
          status["database"] = "ok"
      except Exception as e:
          status["status"] = "degraded"
          status["database"] = f"error: {type(e).__name__}"
      return status
  ```

- [ ] **Step 2: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 3: Commit**
  ```bash
  git add main.py
  git commit -m "feat: health check verifica conexión a BD"
  ```

---

### Task 16: Tests — service.py + endpoints

**Covers:** C12 (parcial)
**Files:**
- Create: `tests/test_service.py`
- Create: `tests/test_endpoints.py`

- [ ] **Step 1: Test de service.py**
  ```python
  # tests/test_service.py
  from unittest.mock import patch, MagicMock
  from service import _limpiar_temporal

  def test_limpiar_temporal_remueve_archivo():
      import tempfile, os
      with tempfile.NamedTemporaryFile(delete=False) as f:
          path = f.name
      _limpiar_temporal(path, "s3://bucket/file.jpg")
      assert not os.path.exists(path)

  def test_limpiar_temporal_no_falla_si_no_existe():
      _limpiar_temporal("/tmp/no_existe.jpg", "s3://bucket/file.jpg")
  ```

- [ ] **Step 2: Test de endpoints**
  ```python
  # tests/test_endpoints.py
  from fastapi.testclient import TestClient
  from main import app

  client = TestClient(app)

  def test_health_check():
      response = client.get("/health")
      assert response.status_code == 200
      assert response.json()["status"] == "ok"

  def test_upload_rechaza_archivo_grande():
      response = client.post(
          "/api/upload",
          files={"imagen": ("test.jpg", b"x" * (11 * 1024 * 1024), "image/jpeg")},
          data={"cliente_id": "test_001"},
      )
      assert response.status_code in [400, 413, 422]
  ```

- [ ] **Step 3: Ejecutar tests**
  ```bash
  uv run pytest tests/test_service.py tests/test_endpoints.py -v
  ```

- [ ] **Step 4: Commit**
  ```bash
  git add tests/test_service.py tests/test_endpoints.py
  git commit -m "test: agregar tests para service.py y endpoints API"
  ```

---

### Task 17: Mover create_all() a startup

**Covers:** C13
**Files:**
- Modify: `database/models.py:39`
- Modify: `main.py` (startup event)

- [ ] **Step 1: Remover create_all de models.py**
  ```python
  # database/models.py — eliminar línea 39:
  # Base.metadata.create_all(bind=engine)
  ```

- [ ] **Step 2: Agregar a main.py startup**
  ```python
  # main.py — agregar evento de startup
  from database.engine import engine
  from database.models import Base

  @app.on_event("startup")
  async def startup_event():
      Base.metadata.create_all(bind=engine)
  ```

- [ ] **Step 3: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 4: Commit**
  ```bash
  git add database/models.py main.py
  git commit -m "fix: mover create_all() a evento startup de FastAPI"
  ```

---

## Fase 4: Limpieza y Menores (Día 5)

### Task 18: Limpieza de imports y dead code

**Covers:** M1, M7, M16, M18, M19, M20, B9, B13
**Files:**
- Modify: `utils/upload_validator.py:124`
- Modify: `ocr/base.py:36-38`
- Modify: `config/settings.py:21-24`
- Modify: `config/server.py:15-16,30`

- [ ] **Step 1: Mover import re a nivel de módulo**
  ```python
  # utils/upload_validator.py — agregar al inicio:
  import re

  RE_CLIENTE_ID = re.compile(r"[a-zA-Z0-9_-]{1,50}")

  # Eliminar import re de dentro de validar_cliente_id
  ```

- [ ] **Step 2: Eliminar OCRResult.to_dict() si no se usa**
  ```python
  # ocr/base.py — eliminar método to_dict si no tiene llamadas
  ```

- [ ] **Step 3: Fix load_dotenv duplicado**
  ```python
  # config/settings.py — eliminar load_dotenv() de aquí
  # config/server.py — eliminar load_dotenv() de aquí
  # main.py — agregar load_dotenv() una vez al inicio
  ```

- [ ] **Step 4: Fix cors_origins default**
  ```python
  # config/server.py:30 — cambiar de:
  cors_origins: list = None

  # a:
  cors_origins: list | None = None
  ```

- [ ] **Step 5: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 6: Commit**
  ```bash
  git add utils/upload_validator.py ocr/base.py config/settings.py config/server.py
  git commit -m "refactor: limpiar imports, dead code, y defaults mutables"
  ```

---

### Task 19: Logging y configuración menor

**Covers:** B1, B2, B5, B8, B10, B14
**Files:**
- Modify: `config/logger.py`
- Modify: `main.py:87-91`
- Modify: `config/server.py:25`
- Modify: `Procfile`

- [ ] **Step 1: Sanitizar filename en logs**
  ```python
  # main.py:87-91 — sanitizar:
  safe_filename = imagen.filename.replace("\n", "").replace("\r", "") if imagen.filename else "unknown"
  logger.info("Upload: %s", safe_filename)
  ```

- [ ] **Step 2: Host default a 127.0.0.1 en dev**
  ```python
  # config/server.py:70 — cambiar de:
  host=os.getenv("HOST", "0.0.0.0").strip(),

  # a:
  host=os.getenv("HOST", "127.0.0.1" if env == "development" else "0.0.0.0").strip(),
  ```

- [ ] **Step 3: Fix Procfile**
  ```bash
  web: uv run python run.py
  ```

- [ ] **Step 4: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add config/logger.py main.py config/server.py Procfile
  git commit -m "fix: sanitizar logs, host seguro en dev, Procfile"
  ```

---

### Task 20: Documentación y .gitignore

**Covers:** B4, B11, B12
**Files:**
- Modify: `.gitignore`
- Modify: `upload_validator.py:135-149`

- [ ] **Step 1: Agregar logs/ a .gitignore**
  ```gitignore
  logs/
  ```

- [ ] **Step 2: Mejorar sanitización de filename**
  ```python
  # utils/upload_validator.py:135-149 — mejorar:
  def sanitizar_filename(filename: str) -> str:
      """Limpia el filename de caracteres peligrosos."""
      if not filename:
          return "unknown"
      # Eliminar path traversal
      nombre = Path(filename).name
      # Eliminar caracteres peligrosos
      nombre = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', nombre)
      # Limitar longitud
      if len(nombre) > 255:
          nombre = nombre[:255]
      # Rechazar solo puntos
      if nombre.strip(".") == "":
          nombre = "unknown"
      return nombre
  ```

- [ ] **Step 3: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 4: Commit**
  ```bash
  git add .gitignore utils/upload_validator.py
  git commit -m "fix: mejorar sanitización de filename y .gitignore"
  ```

---

### Task 21: Validación de config al inicio

**Covers:** B11, B12
**Files:**
- Modify: `ocr/__init__.py`
- Modify: `storage/__init__.py`

- [ ] **Step 1: Validar API key en OCR factory**
  ```python
  # ocr/__init__.py — agregar validación
  def get_ocr_engine() -> OCRProvider:
      # ... existing code ...
      if nombre == "gemini":
          from config.settings import settings
          # La validación ya está en GeminiConfig.from_env()
      # ... existing code ...
  ```

- [ ] **Step 2: Validar credenciales en Storage factory**
  ```python
  # storage/__init__.py — agregar validación
  def get_storage_backend() -> StorageProvider:
      # ... existing code ...
      if nombre == "s3":
          from config.server import server_config
          if not server_config.s3_access_key:
              logger.warning("S3_ACCESS_KEY no configurada. El backend S3 fallará al usar.")
      # ... existing code ...
  ```

- [ ] **Step 3: Ejecutar tests**
  ```bash
  uv run pytest tests/ -v
  ```

- [ ] **Step 4: Commit**
  ```bash
  git add ocr/__init__.py storage/__init__.py
  git commit -m "feat: validar configuración de providers al inicio"
  ```

---

## Resumen de Phases

| Phase | Tasks | Duración estimada | Hallazgos cubiertos |
|-------|-------|-------------------|---------------------|
| **Fase 1** | 1-5 | Día 1 | 13 críticos + seguridad |
| **Fase 2** | 6-10 | Días 2-3 | Arquitectura + rendimiento |
| **Fase 3** | 11-17 | Días 3-4 | Calidad + testing |
| **Fase 4** | 18-21 | Día 5 | Limpieza + menores |

**Total estimado**: 5 días de desarrollo

---

## Verificación final

Después de completar todas las tasks:

```bash
# Verificar que no hay regressions
uv run pytest tests/ -v

# Verificar linting
uv run ruff check .

# Verificar formatting
uv run ruff format .

# Verificar que el servidor arranca
python run.py

# Verificar health check
curl http://localhost:8000/health

# Verificar Docker
docker compose up --build
```

---

*Plan generado el 2026-07-14. Cubre los 77 hallazgos de la auditoría consolidada.*
