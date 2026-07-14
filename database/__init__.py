"""
database — Capa 3: Repositorio.

Punto de entrada único para toda la capa de datos.
Re-exporta exactamente lo mismo que el antiguo database.py:
    engine, SessionLocal, Base, get_db, Comprobante

Así ningún código existente se rompe:
    service.py:  from database import Comprobante   ✅
    main.py:     from database import get_db        ✅
"""

from database.engine import engine, SessionLocal, Base, get_db, DATABASE_URL
from database.models import Comprobante  # noqa: F401  — ejecuta create_all al importar
from config.logger import get_logger

logger = get_logger("database")
logger.info("Tablas verificadas/creadas — motor=%s", DATABASE_URL.split("://")[0])

__all__ = ["engine", "SessionLocal", "Base", "get_db", "Comprobante"]
