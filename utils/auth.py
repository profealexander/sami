"""
auth.py — Autenticación por API key para endpoints protegidos.
"""

import os


def validar_api_key(api_key: str) -> bool:
    """Valida que la API key coincida con la configurada.

    Si no hay key configurada (entorno dev), permite todo.
    """
    key_esperada = os.getenv("SAMI_API_KEY", "")
    if not key_esperada:
        return True  # Sin key configurada, permitir (dev)
    return api_key == key_esperada
