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
├── models.py                Modelos ORM (hoy: Comprobante)
├── backends/
│   ├── __init__.py
│   ├── sqlite.py            Engine SQLite + PRAGMAs (WAL mode, busy timeout)
│   └── postgres.py        Engine PostgreSQL + pool config (pool_size, pool_pre_ping)
```

### Flujo de arranque

```
run.py
  └─ config/server.py  (lee DATABASE_URL del .env)
       └─ database/engine.py
            ├─ ¿sqlite?   → backends/sqlite.py   (crea engine + WAL)
            ├─ ¿postgres? → backends/postgres.py (crea engine + pool)
            └─ define SessionLocal, Base, get_db
       └─ database/models.py  (Comprobante se registra en Base)
       └─ database/__init__.py (re-exporta todo: service.py y main.py no cambian)
```

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
