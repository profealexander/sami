"""
parsers.py — Parser unico de texto OCR.

Carga los patrones desde ocr/patrones_ocr.toml.
Extrae: transfiere, monto, no_comprobante, destinatario.
Retorna un OCRResult listo para usar con model_dump().
"""

import re
import tomllib
from pathlib import Path

from ocr.base import OCRResult

_CONFIG_PATH = Path(__file__).resolve().parent / "patrones_ocr.toml"

with open(_CONFIG_PATH, "rb") as f:
    _cfg = tomllib.load(f)

MESES_ES = _cfg["meses"]
MESES_FALLBACK = _cfg["meses_fallback"]
PATRONES = _cfg["patrones"]

RE_TRANSFIERE = re.compile(PATRONES["transfiere"][0], re.IGNORECASE)
RE_COMPROBANTE = re.compile(PATRONES["no_comprobante"][0], re.IGNORECASE)
RE_MONTO = re.compile(PATRONES["monto"][0], re.IGNORECASE)

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
    """Parsea texto OCR y retorna un OCRResult con los campos extraidos.

    Args:
        texto: Texto crudo extraido por OCR

    Returns:
        OCRResult con los campos poblados (None si no se encontraron)
    """
    result = OCRResult(texto_ocr_crudo=texto.strip() or None)
    esperando_no_comprobante = False

    for linea in texto.split("\n"):
        linea = linea.strip()
        if not linea:
            continue

        if not result.transfiere:
            m = _match_simple(linea, _compilar("transfiere"))
            if m:
                result.transfiere = m.group(1).strip()

        if not result.monto:
            m = _match_simple(linea, _compilar("monto"))
            if m:
                result.monto = m.group(1).replace(",", "")

        if not result.no_comprobante:
            m = _match_simple(linea, _compilar("no_comprobante"))
            if m:
                result.no_comprobante = m.group(1).strip()
            elif esperando_no_comprobante and re.match(r"^\d+$", linea):
                result.no_comprobante = linea
                esperando_no_comprobante = False
            elif _match_simple(linea, _compilar("etiqueta_no_comprobante")):
                esperando_no_comprobante = True

        if not result.destinatario:
            m = _match_simple(linea, _compilar("destinatario"))
            if m:
                result.destinatario = m.group(1).strip()

    return result
