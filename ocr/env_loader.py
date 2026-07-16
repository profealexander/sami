"""
env_loader.py — Carga las variables de entorno específicas del módulo OCR.

Se invoca desde ocr/__init__.py al importar el paquete.
Usa override=False para que las variables del sistema o del .env raíz
tengan prioridad sobre los defaults definidos en ocr/.env.
"""

from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH, override=False)
