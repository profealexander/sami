#!/usr/bin/env python3
"""
Entry point unico de SAMI.

Arranca el servidor en cualquier entorno con la configuracion
del archivo .env o variables de entorno del sistema.

Uso:
    python run.py                    # desarrollo (reload=true)
    ENV=production python run.py     # produccion
"""

import uvicorn
from config.logger import setup_logging, get_logger
from config import settings

if __name__ == "__main__":
    # Inicializar logging ANTES de cualquier otro mensaje
    setup_logging(
        level=settings.log_level,
        log_file=settings.log_file if settings.log_file else None,
        project_root=__import__("pathlib").Path(__file__).parent,
    )

    logger = get_logger("run")
    logger.info("Iniciando servidor — entorno: %s", settings.env)

    # Enmascarar credenciales en el log de BD
    db_url = settings.database_url
    if "@" in db_url:
        db_url = db_url.rsplit("@", maxsplit=1)[-1]  # Eliminar usuario:password@
    logger.info("BD: %s", db_url)
    logger.info("Storage: %s", settings.storage_backend)

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.reload,
        log_level=settings.log_level,
    )
