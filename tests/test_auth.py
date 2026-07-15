"""
test_auth.py — Tests de autenticación por API key.
"""

import os
from unittest.mock import patch

from utils.auth import validar_api_key


def test_api_key_valida():
    with patch.dict(os.environ, {"SAMI_API_KEY": "test_key_123"}):
        assert validar_api_key("test_key_123") is True


def test_api_key_invalida():
    with patch.dict(os.environ, {"SAMI_API_KEY": "test_key_123"}):
        assert validar_api_key("wrong_key") is False


def test_api_key_vacia():
    with patch.dict(os.environ, {"SAMI_API_KEY": ""}):
        assert validar_api_key("any_key") is True


def test_sin_configuracion_permite():
    with patch.dict(os.environ, {}, clear=True):
        assert validar_api_key("any_key") is True
