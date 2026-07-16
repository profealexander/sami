"""
engine.py — Fábrica de engines + Base ORM + Sesión.

Centraliza:
  - Elección del backend según DATABASE_URL
  - declarative_base (Base)
  - sessionmaker (SessionLocal)
  - Dependencia get_db para FastAPI

Así models.py puede importar Base sin imports circulares.
"""

from sqlalchemy.orm import declarative_base, sessionmaker

from config.logger import get_logger
from config.server import server_config
from database.backends.sqlite import create_sqlite_engine
from database.backends.postgres import create_postgres_engine

logger = get_logger("database.engine")

DATABASE_URL = server_config.database_url


# ── Fábrica de engines ──


def create_engine_from_url() -> object:
    """Retorna el engine SQLAlchemy correspondiente a DATABASE_URL."""
    url = DATABASE_URL

    if url.startswith("sqlite"):
        logger.info("Backend: SQLite — %s", url.split("://")[0])
        return create_sqlite_engine(url)

    elif url.startswith("postgresql") or url.startswith("postgres"):
        logger.info("Backend: PostgreSQL — pool_size=%s", server_config.db_pool_size)
        return create_postgres_engine(url, pool_size=server_config.db_pool_size)

    else:
        raise ValueError(
            f"Motor de BD no soportado: {url.split('://')[0]!r}. "
            f"Usa sqlite://... o postgresql://..."
        )


engine = create_engine_from_url()

# ── Base y Sesión ──
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependencia para FastAPI: inyecta sesion de BD."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
