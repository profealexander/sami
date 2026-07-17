"""
test_config.py — Tests de configuracion del servidor (arranque).
"""

from config import settings, Settings


def test_server_config_importa_sin_error():
    assert settings is not None
    assert isinstance(settings, Settings)


def test_server_config_tiene_campos_esperados():
    assert hasattr(settings, "env")
    assert hasattr(settings, "host")
    assert hasattr(settings, "port")
    assert hasattr(settings, "workers")
    assert hasattr(settings, "database_url")
    assert hasattr(settings, "storage_backend")


def test_server_config_tipos_correctos():
    assert isinstance(settings.env, str)
    assert isinstance(settings.host, str)
    assert isinstance(settings.port, int)
    assert isinstance(settings.workers, int)
    assert isinstance(settings.database_url, str)


def test_server_config_host_port_no_vacios():
    assert len(settings.host) > 0
    assert settings.port > 0


def test_server_config_env_valido():
    assert settings.env in ("development", "production")


def test_settings_get_settings_cache():
    from config.settings import get_settings

    assert get_settings() is settings
    assert get_settings() is get_settings()
