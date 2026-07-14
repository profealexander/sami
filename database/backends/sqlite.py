"""
backends/sqlite.py — Engine específico para SQLite.

Contiene TODA la configuración particular de SQLite:
PRAGMAs, connect_args, timeouts, etc.
Nada de esto afecta a otros motores de BD.
"""

from sqlalchemy import create_engine, text


def create_sqlite_engine(database_url: str):
    """Crea y configura engine SQLite con WAL mode."""
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    # WAL mode + busy timeout para escritura concurrente
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA busy_timeout=5000"))
    return engine
