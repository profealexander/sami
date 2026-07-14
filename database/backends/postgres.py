"""
backends/postgres.py — Engine específico para PostgreSQL.

Contiene TODA la configuración particular de PostgreSQL:
pool_size, pool_pre_ping, timeout, etc.
Nada de esto afecta a SQLite.
"""

from sqlalchemy import create_engine


def create_postgres_engine(database_url: str, pool_size: int = 10):
    """Crea y configura engine PostgreSQL con pool de conexiones."""
    engine = create_engine(
        database_url,
        pool_size=pool_size,
        pool_pre_ping=True,
    )
    return engine
