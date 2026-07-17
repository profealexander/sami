"""
test_config.py — Tests de configuracion del servidor (arranque).
"""

from config.server import ServerConfig, server_config


def test_server_config_importa_sin_error():
    assert server_config is not None
    assert isinstance(server_config, ServerConfig)


def test_server_config_tiene_campos_esperados():
    assert hasattr(server_config, "env")
    assert hasattr(server_config, "host")
    assert hasattr(server_config, "port")
    assert hasattr(server_config, "workers")
    assert hasattr(server_config, "database_url")
    assert hasattr(server_config, "storage_backend")


def test_server_config_tipos_correctos():
    assert isinstance(server_config.env, str)
    assert isinstance(server_config.host, str)
    assert isinstance(server_config.port, int)
    assert isinstance(server_config.workers, int)
    assert isinstance(server_config.database_url, str)


def test_server_config_host_port_no_vacios():
    assert len(server_config.host) > 0
    assert server_config.port > 0


def test_server_config_env_valido():
    assert server_config.env in ("development", "production")
