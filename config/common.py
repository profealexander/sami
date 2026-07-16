"""
common.py — Constantes compartidas de configuración.
"""

from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Cargar .env una sola vez, antes de que cualquier módulo lea os.getenv()
load_dotenv(PROJECT_ROOT / ".env", override=False)
