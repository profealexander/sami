"""
parsers.py — Parser unico de texto OCR.

Carga los patrones desde ocr/patrones_ocr.toml.
Extrae solo: transfiere, monto, no_comprobante.
El texto completo del OCR se propaga sin parsear para guardarlo.
"""

import re
import tomllib
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent / "patrones_ocr.toml"

with open(_CONFIG_PATH, "rb") as f:
    _cfg = tomllib.load(f)

MESES_ES = _cfg["meses"]
MESES_FALLBACK = _cfg["meses_fallback"]
PATRONES = _cfg["patrones"]

RE_CAJERO = re.compile(PATRONES["cajero"][0], re.IGNORECASE)
# RE_FECHA = re.compile(PATRONES["fecha_numerica"][0])       # Disponible para uso futuro
# RE_HORA = re.compile(PATRONES["hora"][0], re.IGNORECASE)  # Disponible para uso futuro
RE_VENTA = re.compile(PATRONES["no_venta"][0], re.IGNORECASE)
RE_MONTO = re.compile(PATRONES["monto"][0], re.IGNORECASE)
# RE_DESTINATARIO = re.compile(PATRONES["destinatario"][1], re.IGNORECASE)  # Disponible para uso futuro

_regex_cache = {}


def _compilar(nombre):
    if nombre not in _regex_cache:
        _regex_cache[nombre] = [re.compile(p, re.IGNORECASE) for p in PATRONES[nombre]]
    return _regex_cache[nombre]


def _match_simple(linea, regex_list):
    for r in regex_list:
        m = r.search(linea)
        if m:
            return m
    return None


def parsear_campos(texto):
    """Parsea texto OCR y extrae campos estructurados.

    Args:
        texto: Texto crudo extraido por OCR

    Returns:
        Dict con transfiere, monto, no_comprobante, texto_completo
    """
    resultado = {
        "transfiere": None,
        "monto": None,
        "no_comprobante": None,
        "texto_completo": texto.strip(),
    }

    for linea in texto.split("\n"):
        linea = linea.strip()
        if not linea:
            continue

        if not resultado["transfiere"]:
            m = _match_simple(linea, _compilar("cajero"))
            if m:
                resultado["transfiere"] = m.group(1).strip()

        if not resultado["monto"]:
            m = _match_simple(linea, _compilar("monto"))
            if m:
                resultado["monto"] = m.group(1).replace(",", "")

        if not resultado["no_comprobante"]:
            m = _match_simple(linea, _compilar("no_venta"))
            if m:
                resultado["no_comprobante"] = m.group(1).strip()

    return resultado
