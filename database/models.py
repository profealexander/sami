"""
models.py — Modelos ORM (SQLAlchemy).

Separa la definición de las tablas de la config del engine.
Cada modelo hereda de Base (definida en database.engine).
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from database.engine import Base, engine


class Comprobante(Base):
    """Modelo ORM de la tabla comprobantes.

    Almacena los campos extraidos por OCR y metadatos del envio.
    Cada fila representa un comprobante procesado.
    """
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
