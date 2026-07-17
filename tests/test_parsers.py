"""
test_parsers.py — Tests de parsers OCR compartidos.
"""

from ocr.parsers import parsear_campos, RE_TRANSFIERE, RE_COMPROBANTE, RE_MONTO


def test_parsear_transfiere():
    texto = "CAJERO: Juan Pérez"
    resultado = parsear_campos(texto)
    assert resultado["transfiere"] == "Juan Pérez"


def test_parsear_transfiere_atendio():
    texto = "ATENDIO: Maria Lopez"
    resultado = parsear_campos(texto)
    assert resultado["transfiere"] == "Maria Lopez"


def test_parsear_transfiere_remitente():
    texto = "De Juan Perez"
    resultado = parsear_campos(texto)
    assert resultado["transfiere"] == "Juan Perez"


def test_parsear_no_comprobante():
    texto = "VENTA: 12345"
    resultado = parsear_campos(texto)
    assert resultado["no_comprobante"] == "12345"


def test_parsear_no_comprobante_con_n():
    texto = "N° de venta: 0012481545"
    resultado = parsear_campos(texto)
    assert resultado["no_comprobante"] == "0012481545"


def test_parsear_no_comprobante_con_folio():
    texto = "FOLIO: 98765"
    resultado = parsear_campos(texto)
    assert resultado["no_comprobante"] == "98765"


def test_parsear_monto():
    texto = "TOTAL: $1,234.56"
    resultado = parsear_campos(texto)
    assert resultado["monto"] == "1234.56"


def test_parsear_monto_sin_etiqueta():
    texto = "$ 27.83"
    resultado = parsear_campos(texto)
    assert resultado["monto"] == "27.83"


def test_parsear_multiples_campos():
    texto = """CAJERO: Pedro Gomez
VENTA: 99999
TOTAL: $500.00"""
    resultado = parsear_campos(texto)
    assert resultado["transfiere"] == "Pedro Gomez"
    assert resultado["no_comprobante"] == "99999"
    assert resultado["monto"] == "500.00"


def test_parsear_texto_vacio():
    resultado = parsear_campos("")
    assert resultado["transfiere"] is None
    assert resultado["no_comprobante"] is None
    assert resultado["monto"] is None


def test_regex_compilados():
    assert RE_TRANSFIERE is not None
    assert RE_COMPROBANTE is not None
    assert RE_MONTO is not None


def test_texto_completo_incluido():
    resultado = parsear_campos("  Hola mundo  ")
    assert resultado["texto_completo"] == "Hola mundo"


def test_parsear_comprobante_pichincha():
    texto = """$ 20.00
A Barvecho Ordoñez Maria Cristina
El 06 de julio de 2026
De Guzman Guzman Lorena
Cuenta destino: *** *** 3273
N° de comprobante: 94644154"""
    resultado = parsear_campos(texto)
    assert resultado["transfiere"] == "Guzman Guzman Lorena"
    assert resultado["monto"] == "20.00"
    assert resultado["no_comprobante"] == "94644154"
    assert "N° de comprobante: 94644154" in resultado["texto_completo"]
