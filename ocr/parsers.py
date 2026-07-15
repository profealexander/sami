"""
parsers.py — Parsers compartidos para providers OCR.

Contiene regex pre-compilados y funciones de parsing
usadas por tesseract_provider y ocrspace_provider.
"""

import re

# ── Regex pre-compilados ──
RE_CAJERO = re.compile(r'(?:CAJERO|ATENDIO|VENDEDOR|EMPLEADO)\s*[\:\-]?\s*(.+)', re.IGNORECASE)
RE_FECHA = re.compile(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})')
RE_HORA = re.compile(r'(\d{1,2}):(\d{2})')
RE_VENTA = re.compile(r'(?:VENTA|TICKET|FOLIO|NO\.?\s*VENTA)\s*[\:\-]?\s*(\d+)', re.IGNORECASE)
RE_MONTO = re.compile(r'(?:MONTO|TOTAL|IMPORTE|PAGO)\s*[\:\-]?\s*\$?\s*([\d,]+\.?\d*)', re.IGNORECASE)
RE_DESTINATARIO = re.compile(r'(?:DESTINATARIO|PARA|BENEFICIARIO)\s*[\:\-]?\s*(.+)', re.IGNORECASE)

# ── Meses en español ──
MESES_ES = {
    "ENERO": "01", "FEBRERO": "02", "MARZO": "03", "ABRIL": "04",
    "MAYO": "05", "JUNIO": "06", "JULIO": "07", "AGOSTO": "08",
    "SEPTIEMBRE": "09", "OCTUBRE": "10", "NOVIEMBRE": "11", "DICIEMBRE": "12",
}

MESES_FALLBACK = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}


def parsear_campos(texto: str) -> dict:
    """Parsea texto OCR y extrae campos estructurados.

    Args:
        texto: Texto crudo extraído por OCR

    Returns:
        Dict con cajero, fecha, hora, no_venta, monto, destinatario
    """
    lineas = texto.split('\n')
    resultado = {
        "cajero": None,
        "fecha": None,
        "hora": None,
        "no_venta": None,
        "monto": None,
        "destinatario": None,
    }

    for linea in lineas:
        if not resultado["cajero"]:
            match = RE_CAJERO.search(linea)
            if match:
                resultado["cajero"] = match.group(1).strip()

        if not resultado["fecha"]:
            match = RE_FECHA.search(linea)
            if match:
                dia, mes, anio = match.group(1), match.group(2), match.group(3)
                resultado["fecha"] = f"{dia.zfill(2)}/{mes.zfill(2)}/{anio}"

        if not resultado["hora"]:
            match = RE_HORA.search(linea)
            if match:
                resultado["hora"] = f"{match.group(1).zfill(2)}:{match.group(2)}"

        if not resultado["no_venta"]:
            match = RE_VENTA.search(linea)
            if match:
                resultado["no_venta"] = match.group(1)

        if not resultado["monto"]:
            match = RE_MONTO.search(linea)
            if match:
                resultado["monto"] = match.group(1).replace(",", "")

        if not resultado["destinatario"]:
            match = RE_DESTINATARIO.search(linea)
            if match:
                resultado["destinatario"] = match.group(1).strip()

    return resultado
