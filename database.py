"""
database.py — Capa 3: Repositorio SQLite/PostgreSQL.

Lee DATABASE_URL de config.server, no tiene valores hardcodeados.
Soporta SQLite (local) y PostgreSQL (produccion) sin cambiar codigo.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

from config.server import server_config


# ── Motor: SQLite o PostgreSQL segun DATABASE_URL ──
DATABASE_URL = server_config.database_url

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL / otro
    engine = create_engine(
        DATABASE_URL,
        pool_size=server_config.db_pool_size,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Comprobante(Base):
    __tablename__ = "comprobantes"

    id = Column(Integer, primary_key=True, index=True)
    # Datos extraidos por OCR
    cajero = Column(String, nullable=True)
    fecha_comprobante = Column(String, nullable=True)
    hora_comprobante = Column(String, nullable=True)
    no_venta = Column(String, nullable=True)

    # Metadatos del envio
    cliente_id = Column(String, index=True)
    fecha_envio = Column(DateTime, default=datetime.utcnow)

    # Respaldo: ruta o URL de la imagen original
    ruta_imagen = Column(String)


# Crear tablas si no existen
Base.metadata.create_all(bind=engine)


def get_db():
    """Dependencia para FastAPI: inyecta sesion de BD."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
