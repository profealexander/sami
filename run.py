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
from config.server import server_config

if __name__ == "__main__":
    print(f"[SAMI] Iniciando servidor - entorno: {server_config.env}")
    print(f"[SAMI] BD: {server_config.database_url}")
    print(f"[SAMI] Storage: {server_config.storage_backend}")

    uvicorn.run(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        workers=server_config.workers,
        reload=server_config.reload,
        log_level=server_config.log_level,
    )
