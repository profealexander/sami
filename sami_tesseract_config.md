# SAMI — Configuracion de Tesseract OCR

> Documentacion del proveedor OCR por defecto de SAMI.

---

## Requisitos

- **Tesseract 5.x** instalado en `C:\Program Files\Tesseract-OCR\`
- **Idioma espanol** (`spa`) ya incluido en la instalacion
- `pytesseract` y `Pillow` instalados en el entorno Python

---

## Variables de entorno (`.env`)

El comportamiento de Tesseract se configura desde el archivo `.env`:

| Variable | Valor por defecto | Descripcion |
|---|---|---|
| `TESSERACT_CMD` | (auto-detecta) | Ruta al ejecutable de Tesseract |
| `TESSERACT_LANG` | `spa` | Idioma para OCR |
| `TESSERACT_SCALE` | `2.0` | Escalar imagen antes de OCR (mejora precision) |
| `TESSERACT_THRESHOLD` | `0` | Binarizacion: `0`=Otsu automatico, `1-254`=manual, `255`=sin binarizar |
| `TESSERACT_DENOISE` | `true` | Eliminar ruido con filtro mediana |
| `TESSERACT_PSM` | `3` | Page Segmentation Mode de Tesseract |

### Ejemplo `.env`
```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_LANG=spa
TESSERACT_SCALE=2.0
TESSERACT_THRESHOLD=0
TESSERACT_DENOISE=true
TESSERACT_PSM=3
```

---

## Preprocesamiento de imagen

El `TesseractProvider` aplica estas transformaciones automaticamente:

1. **Escalado** (`TESSERACT_SCALE`): duplica el tamano de la imagen para mejorar reconocimiento de texto pequeno en fotos de celular
2. **Escala de grises**: convierte a blanco y negro
3. **Filtro mediana** (`TESSERACT_DENOISE`): elimina ruido tipo "arena" de fotos con poca luz
4. **Binarizacion** (`TESSERACT_THRESHOLD`): convierte a blanco puro y negro puro para maximizar contraste

---

## Page Segmentation Modes (PSM)

| PSM | Descripcion | Cuando usarlo |
|---|---|---|
| `3` | Segmentacion automatica (defecto) | Comprobantes con layout variado |
| `4` | Texto de tamano uniforme | Facturas con tipografia consistente |
| `6` | Bloque de texto uniforme | Parrafos largos |
| `7` | Linea unica de texto | Una sola linea |
| `11` | Texto sin orden | Comprabantes desordenados |
| `12` | Bloque de texto con orientacion variable | |

**Recomendado para comprobantes**: `PSM=3` (automatico)

---

## Compatibilidad con formatos de comprobantes

Actualmente las regex de extraccion (`ocr/tesseract_provider.py`) estan disenadas para:

- **Tickets de compra/venta**: busca "Cajero", "Venta", "Ticket", "Factura", "No."
- **Fechas**: formato DD/MM/AAAA o DD-MM-AAAA
- **Horas**: formato HH:MM

Si necesitas extraer campos de **transferencias bancarias** (Banco Pichincha, etc.), hay que agregar patrones adicionales como:
- Monto: `$XX.XX`
- Destinatario: despues de "A "
- Remitente: despues de "De "
- Fecha: "El DD de mes de AAAA"

---

## Prueba rapida del OCR

```bash
python -c "
import os
os.environ['PATH'] += r';C:\Program Files\Tesseract-OCR'
import pytesseract
from PIL import Image
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

img = Image.open('ruta/a/tu/comprobante.jpg')
texto = pytesseract.image_to_string(img, lang='spa')
print(texto)
"
```

---

## Solucion de problemas

| Problema | Causa | Solucion |
|---|---|---|
| `pytesseract.pytesseract.TesseractNotFoundError` | Tesseract no encontrado | Verificar `TESSERACT_CMD` o instalacion |
| Texto con caracteres raros | Idioma incorrecto | Usar `lang='spa'` |
| OCR lento | Escala muy alta | Reducir `TESSERACT_SCALE` a `1.5` |
| No detecta texto pequeno | Escala muy baja | Aumentar `TESSERACT_SCALE` a `3.0` |
| Fondo manchado afecta resultado | Ruido en la imagen | Activar `TESSERACT_DENOISE=true` |
