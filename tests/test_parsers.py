"""
test_parsers.py — Tests de parsers OCR compartidos.
"""

from ocr.parsers import parsear_campos, RE_CAJERO, RE_FECHA, RE_HORA


def test_parsear_cajero():
    texto = "CAJERO: Juan Pérez"
    resultado = parsear_campos(texto)
    assert resultado["cajero"] == "Juan Pérez"


def test_parsear_fecha():
    texto = "Fecha: 15/07/2026"
    resultado = parsear_campos(texto)
    assert resultado["fecha"] == "15/07/2026"


def test_parsear_hora():
    texto = "Hora: 14:30"
    resultado = parsear_campos(texto)
    assert resultado["hora"] == "14:30"


def test_parsear_venta():
    texto = "VENTA: 12345"
    resultado = parsear_campos(texto)
    assert resultado["no_venta"] == "12345"


def test_parsear_monto():
    texto = "TOTAL: $1,234.56"
    resultado = parsear_campos(texto)
    assert resultado["monto"] == "1234.56"


def test_parsear_destinatario():
    texto = "DESTINATARIO: Maria Lopez"
    resultado = parsear_campos(texto)
    assert resultado["destinatario"] == "Maria Lopez"


def test_regex_compilados():
    assert RE_CAJERO is not None
    assert RE_FECHA is not None
    assert RE_HORA is not None


def test_parsear_multiples_campos():
    texto = """CAJERO: Pedro Gomez
Fecha: 20/12/2025
Hora: 09:15
VENTA: 99999
TOTAL: $500.00"""
    resultado = parsear_campos(texto)
    assert resultado["cajero"] == "Pedro Gomez"
    assert resultado["fecha"] == "20/12/2025"
    assert resultado["hora"] == "09:15"
    assert resultado["no_venta"] == "99999"
    assert resultado["monto"] == "500.00"


def test_parsear_texto_vacio():
    resultado = parsear_campos("")
    assert resultado["cajero"] is None
    assert resultado["fecha"] is None
