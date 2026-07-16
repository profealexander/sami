"""
models.py — Modelos ORM (SQLAlchemy).

Separa la definición de las tablas de la config del engine.
Cada modelo hereda de Base (definida en database.engine).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime

from database.engine import Base


class Comprobante(Base):
    """Modelo ORM de la tabla comprobantes."""

    __tablename__ = "comprobantes"

    id = Column(Integer, primary_key=True, index=True)
    transfiere = Column(String, nullable=True)
    no_comprobante = Column(String, nullable=True)
    monto = Column(String, nullable=True)
    texto_ocr_crudo = Column(Text, nullable=True)

    cliente_id = Column(String, index=True)
    fecha_envio = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ruta_imagen = Column(String)
