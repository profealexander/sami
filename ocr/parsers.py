"""
parsers.py — Parser unico de texto OCR.

Consume los patrones de config/patrones_ocr.py.
Todos los providers llaman a parsear_campos() en vez de tener su propio parsing.
"""

import re

from config.patrones_ocr import PATRONES, MESES_ES, MESES_FALLBACK

RE_CAJERO = re.compile(PATRONES["cajero"][0], re.IGNORECASE)
RE_FECHA = re.compile(PATRONES["fecha_numerica"][0])
RE_HORA = re.compile(PATRONES["hora"][0], re.IGNORECASE)
RE_VENTA = re.compile(PATRONES["no_venta"][0], re.IGNORECASE)
RE_MONTO = re.compile(PATRONES["monto"][1], re.IGNORECASE)
RE_DESTINATARIO = re.compile(PATRONES["destinatario"][1], re.IGNORECASE)

_regex_cache = {}


def _compilar(nombre):
    if nombre not in _regex_cache:
        _regex_cache[nombre] = [
            re.compile(p, re.IGNORECASE) for p in PATRONES[nombre]
        ]
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
        Dict con cajero, fecha, hora, no_venta, monto, destinatario
    """
    resultado = {
        "cajero": None, "fecha": None, "hora": None,
        "no_venta": None, "monto": None, "destinatario": None,
    }

    for linea in texto.split("\n"):
        linea = linea.strip()
        if not linea:
            continue

        # ── Cajero ──
        if not resultado["cajero"]:
            m = _match_simple(linea, _compilar("cajero"))
            if m:
                resultado["cajero"] = m.group(1).strip()

        # ── Destinatario ──
        if not resultado["destinatario"]:
            m = _match_simple(linea, _compilar("destinatario"))
            if m:
                resultado["destinatario"] = m.group(1).strip()

        # ── Monto ──
        if not resultado["monto"]:
            m = _match_simple(linea, _compilar("monto"))
            if m:
                resultado["monto"] = m.group(1).replace(",", "")

        # ── Fecha numerica (dd/mm/aaaa) ──
        if not resultado["fecha"]:
            for r in _compilar("fecha_numerica"):
                m = r.search(linea)
                if m:
                    d, mes, a = m.group(1), m.group(2), m.group(3)
                    if 1 <= int(d) <= 31 and 1 <= int(mes) <= 12:
                        resultado["fecha"] = f"{int(d):02d}/{int(mes):02d}/{a}"
                        break

        # ── Fecha textual (El dd de mes de aaaa) ──
        if not resultado["fecha"]:
            for r in _compilar("fecha_textual"):
                m = r.search(linea)
                if m:
                    dia, mes_str, anio = m.group(1), m.group(2).lower(), m.group(3)
                    mes_num = MESES_ES.get(mes_str)
                    if not mes_num:
                        mes_corregido = MESES_FALLBACK.get(mes_str)
                        if mes_corregido:
                            mes_num = MESES_ES.get(mes_corregido)
                    if mes_num:
                        resultado["fecha"] = f"{int(dia):02d}/{mes_num:02d}/{anio}"
                    break

        # ── Hora ──
        if not resultado["hora"]:
            for r in _compilar("hora"):
                m = r.search(linea)
                if m:
                    h, mi = int(m.group(1)), int(m.group(2))
                    if 0 <= h <= 23 and 0 <= mi <= 59:
                        resultado["hora"] = f"{h:02d}:{mi:02d}"
                    break

        # ── Numero de comprobante ──
        if not resultado["no_venta"]:
            m = _match_simple(linea, _compilar("no_venta"))
            if m:
                resultado["no_venta"] = m.group(1).strip()

    return resultado
