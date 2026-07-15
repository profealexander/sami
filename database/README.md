# Capa 3 — Repositorio (`database/`)

Paquete que encapsula el acceso a base de datos. Soporta **SQLite** (local) y
**PostgreSQL** (produccion) con el mismo codigo; el motor se elige automaticamente
segun `DATABASE_URL` en `.env`.

---

## Estructura

```
database/
├── __init__.py              Re-exporta: engine, SessionLocal, Base, get_db, Comprobante
├── engine.py                Fabrica: elige backend segun DATABASE_URL + define Base/Session
├── models.py                Modelos ORM (Comprobante)
├── backends/
│   ├── __init__.py
│   ├── sqlite.py            Engine SQLite + PRAGMAs (WAL mode, busy timeout, pool_pre_ping)
│   └── postgres.py          Engine PostgreSQL + pool config (pool_size, pool_pre_ping)
```

### Modelo Comprobante

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| id | Integer | Primary key, auto-increment |
| cajero | String | Nombre del cajero (OCR) |
| fecha_comprobante | String | Fecha DD/MM/AAAA (OCR) |
| hora_comprobante | String | Hora HH:MM (OCR) |
| no_venta | String | Numero de venta/ticket (OCR) |
| monto | String | Monto detectado (OCR) |
| destinatario | String | Destinatario para transferencias (OCR) |
| cliente_id | String | Identificador del cliente (indexado) |
| fecha_envio | DateTime | Timestamp UTC de cuando se recibio |
| ruta_imagen | String | Ruta local o URL de la imagen |

---

## Flujo de arranque

```
run.py
  └─ config/server.py  (lee DATABASE_URL del .env)
       └─ database/engine.py
            ├─ ¿sqlite?   → backends/sqlite.py   (crea engine + WAL + pool_pre_ping)
            ├─ ¿postgres? → backends/postgres.py (crea engine + pool + pool_pre_ping)
            └─ define SessionLocal, Base, get_db
       └─ database/models.py  (Comprobante se registra en Base)
       └─ database/__init__.py (re-exporta todo: service.py y main.py no cambian)

@startup event en main.py:
  └─ Base.metadata.create_all(bind=engine)  ← Crea tablas al arrancar
```

**Nota**: `create_all()` se ejecuta en el evento `@app.on_event("startup")`, NO al importar models.py.

---

## Como anadir un nuevo motor de BD

Ejemplo: MySQL.

```python
# 1. Crear database/backends/mysql.py
def create_mysql_engine(database_url: str, pool_size: int = 10):
    engine = create_engine(database_url, pool_size=pool_size, pool_pre_ping=True)
    return engine

# 2. Registrar en database/engine.py
elif url.startswith("mysql"):
    logger.info("Backend: MySQL — pool_size=%s", server_config.db_pool_size)
    return create_mysql_engine(url, pool_size=server_config.db_pool_size)
```

Sin tocar `models.py`, `__init__.py`, `service.py` ni `main.py`.

---

## Como anadir un nuevo modelo ORM

```python
# En database/models.py
class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    ...

# Opcional: si quieres import directo desde database
# En database/__init__.py añadir:
# from database.models import Cliente
# __all__.append("Cliente")
```

---

## Backends disponibles

### SQLite (`backends/sqlite.py`)

| Config | Valor |
|---|---|
| Archivo | `comprobantes.db` (segun DATABASE_URL) |
| WAL mode | Activado (`PRAGMA journal_mode=WAL`) |
| Busy timeout | 5 segundos (`PRAGMA busy_timeout=5000`) |
| check_same_thread | False (permite multi-worker en desarrollo) |
| pool_pre_ping | True (verifica conexion antes de usarla) |

### PostgreSQL (`backends/postgres.py`)

| Config | Default |
|---|---|
| Pool size | 10 (configurable via `DB_POOL_SIZE` en .env) |
| pool_pre_ping | True (verifica conexion antes de usarla) |

Usado solo cuando `DATABASE_URL` empieza con `postgresql://`.

---

## Dependencia para FastAPI

`get_db()` se inyecta en las rutas automaticamente:

```python
from database import get_db

@app.post("/api/upload")
def upload(file: UploadFile, db: Session = Depends(get_db)):
    ...
```

Cierra la sesion al finalizar la peticion (haya funcionado o no).

---

## ComprobanteResponse

`service.py` retorna `ComprobanteResponse` en lugar de monkey-patching atributos en el ORM:

```python
@dataclass
class ComprobanteResponse:
    registro: Comprobante
    monto: str | None
    destinatario: str | None
    ocr_exitoso: bool
    proveedor_ocr: str | None
```

Esto separa la representacion de la API del modelo de persistencia.
