"""
logger.py — Configuración centralizada del logging de SAMI.

Reemplaza todos los print() del proyecto por logging estructurado.
Usa el módulo logging de la stdlib (sin dependencias externas).

Formato:
    [SAMI] 2026-07-13 23:00:00 | NIVEL | módulo | mensaje
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


# ── Formato unificado ──
LOG_FORMAT = "[SAMI] %(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger con el nombre del módulo.

    Args:
        name: Nombre del módulo (ej: 'service', 'gemini', 'storage.local')

    Returns:
        Logger configurado con el formato SAMI
    """
    return logging.getLogger(f"sami.{name}")


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> None:
    """Configura el sistema de logging global de SAMI.

    Args:
        level: Nivel mínimo de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Nombre del archivo de log (opcional)
        project_root: Ruta raíz del proyecto (para resolver ruta de logs)

    Uso:
        from config.logger import setup_logging
        setup_logging(level="INFO", log_file="sami.log")
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # ── Handler de consola (siempre activo) ──
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))

    # ── Configurar logger raíz sami ──
    root_logger = logging.getLogger("sami")
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # ── Handler de archivo rotativo (opcional) ──
    if log_file and project_root:
        log_dir = project_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / log_file

        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(log_path),
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(
            logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        )
        root_logger.addHandler(file_handler)

    # ── Silenciar loggers ruidosos de terceros ──
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # ── Mensaje de bienvenida ──
    logger = get_logger("logger")
    logger.info("Logging iniciado — nivel=%s", level)
    if log_file:
        logger.info("Archivo de log: %s", str(log_dir / log_file))
