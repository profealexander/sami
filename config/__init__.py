"""
config — Configuracion unificada de SAMI.

Uso:
    from config import settings, PROJECT_ROOT, get_settings
"""

from config.settings import PROJECT_ROOT, Settings, get_settings, settings

__all__ = ["PROJECT_ROOT", "Settings", "get_settings", "settings"]
