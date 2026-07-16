"""
patrones_ocr.py — Patrones de extraccion OCR configurables.

Edita este archivo para ajustar los regex sin tocar los providers.
Cada entrada en PATRONES es un campo con una lista de patrones regex.
El primer patron que haga match se usa (orden de prioridad).

Formato:
    "nombre_campo": [
        r"patron_regex_1",  # Primer intento
        r"patron_regex_2",  # Fallback si el primero no matchea
    ]

Los grupos de captura deben ser los valores a extraer.
Para patrones con multiples grupos (ej. fecha), el parser principal
los procesa segun la cantidad de grupos capturados.
"""

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

MESES_FALLBACK = {
    "jullo": "julio", "junlo": "junio", "julio": "julio",
    "enero": "enero", "febrero": "febrero", "marzo": "marzo",
    "abril": "abril", "mayo": "mayo", "agosto": "agosto",
    "setiembre": "septiembre", "octubre": "octubre",
    "noviembre": "noviembre", "diziembre": "diciembre",
}

PATRONES = {
    "cajero": [
        r'(?:CAJERO|ATENDIO|ATENDIO|CAJER@|VENDEDOR|EMPLEADO)\s*[\:\-]?\s*(.+)',
        r'^De\s+(.+)$',
    ],
    "destinatario": [
        r'^A\s+(.+)$',
        r'(?:DESTINATARIO|PARA|BENEFICIARIO)\s*[\:\-]?\s*(.+)',
    ],
    "monto": [
        r'(?:MONTO|TOTAL|IMPORTE|PAGO)\s*[\:\-]?\s*\$?\s*([\d,]+\.?\d*)',
        r'\$\s*([\d,]+\.?\d*)',
    ],
    "fecha_numerica": [
        r'(\d{1,2})[\-\.\/](\d{1,2})[\-\.\/](\d{2,4})',
    ],
    "fecha_textual": [
        r'El\s+(\d{1,2})\s+de\s+([a-z\240-\377]+)\s+de\s+(\d{4})',
    ],
    "hora": [
        r'(\d{1,2}):(\d{2})(?::(\d{2}))?',
    ],
    "no_venta": [
        r'(?:VENTA|TICKET|FACTURA|COMPROBANTE)\s*[\:\-]?\s*(\d[\d\-/]*)',
        r'(?:No\.?|N|NUMERO|FOLIO)\s*[\:\-]?\s*(\d[\d\-]*)',
        r'N[\*\u00B0]\s*de\s+(?:comprobante|venta|ticket)\s*[\:\-]?\s*(\d[\d\-]*)',
        r'(?:No\.?\s*VENTA|NO\.?\s*VENTA)\s*[\:\-]?\s*(\d+)',
    ],
}
