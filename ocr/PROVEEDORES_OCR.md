# Proveedores OCR — SAMI

Documentación de los proveedores OCR disponibles en SAMI,
con enlaces oficiales, type de API, autenticación y límites.

---

## 1. Google Gemini API (principal)

| Campo | Valor |
|---|---|
| **Tipo** | API cloud (IA multimodal) |
| **Paquete Python** | `google-genai` |
| **Documentación oficial** | https://ai.google.dev/gemini-api/docs |
| **Consola / API Keys** | https://aistudio.google.com/app/apikey |
| **Precios** | https://ai.google.dev/pricing |
| **Modelo usado** | `gemini-2.0-flash` |
| **Autenticación** | API Key vía `GEMINI_API_KEY` en `.env` |
| **Límite gratis** | 1,500 requests/día |
| **Idiomas** | Multilenguaje natural, detecta automáticamente |

**Ventajas:** Extrae campos estructurados directamente (entiende contexto).
**Desventajas:** Requiere internet, cuota diaria limitada en tier gratis.

**Optimizaciones implementadas:**
- Singleton: reutiliza `genai.Client` across requests
- Compresión automática si imagen > 1MB (JPEG 85% quality)
- MIME type detectado desde extensión del archivo

---

## 2. Tesseract OCR (fallback local)

| Campo | Valor |
|---|---|
| **Tipo** | Motor OCR local (sin internet) |
| **Paquete Python** | `pytesseract` |
| **Repositorio oficial** | https://github.com/tesseract-ocr/tesseract |
| **Binarios Windows** | https://github.com/UB-Mannheim/tesseract/releases |
| **Documentación pytesseract** | https://github.com/madmaze/pytesseract |
| **Idioma español** | `tesseract-ocr-spa` (traineddata) |
| **Autenticación** | Ninguna (local) |
| **Límite** | Ilimitado |

**Instalación en Linux:**
```bash
sudo -S -p '' apt install tesseract-ocr tesseract-ocr-spa
```

**Instalación en Windows:**
1. Descargar installer desde UB-Mannheim releases
2. Ejecutar y marcar "Spanish" durante la instalación
3. Opcional: definir `TESSERACT_CMD` en `.env` si la ruta no es estándar

**Ventajas:** Sin dependencia de internet, sin límites, sin API keys.
**Desventajas:** Menor precisión que APIs cloud, no entiende contexto.

**Optimizaciones implementadas:**
- Cache de preprocesamiento (hash de imagen + config)
- Umbral Otsu optimizado con `histogram()` (100x menos RAM)
- Regex pre-compilados en `ocr/parsers.py`

---

## 3. OCR.space API

| Campo | Valor |
|---|---|
| **Tipo** | API cloud (OCR tradicional) |
| **Paquete Python** | `requests` (nativo) |
| **Sitio oficial** | https://ocr.space/ |
| **Documentación API** | https://ocr.space/ocrapi |
| **Consola / API Keys** | https://ocr.space/ (registro gratuito) |
| **Autenticación** | API Key vía `OCRSPACE_API_KEY` en `.env` |
| **Límite gratis** | 25,000 requests/mes, 500/día por IP |
| **Límite archivo** | 1 MB por imagen (gratis) |
| **Engine** | `OCREngine=2` (más moderno) |

**Ventajas:** 25,000 requests/mes gratis, simple de integrar.
**Desventajas:** OCR tradicional (no entiende contexto), límite de 1 MB.

**Optimizaciones implementadas:**
- Compresión automática si imagen > 1MB
- Regex pre-compilados en `ocr/parsers.py`

---

## Comparativa rápida

| Característica | Gemini | Tesseract | OCR.space |
|---|---|---|---|
| Internet requerido | Sí | No | Sí |
| Precisión en tickets | 95%+ | 80-90% | 85-92% |
| Entiende contexto | Sí | No | No |
| Costo | Gratis 1,500/día | Gratis | Gratis 25k/mes |
| Velocidad | 2-5 seg | 1-3 seg | 3-10 seg |
| Ideal para | Producción con internet | Offline / respaldo | Alto volumen gratis |

---

## Circuit Breaker

El `FallbackProvider` incluye un circuit breaker que protege contra APIs degradadas:

- **Threshold**: 5 fallos consecutivos
- **Timeout**: 60 segundos
- **Comportamiento**: Si el proveedor primario falla 5 veces seguidas, se bloquea temporalmente y se usa directamente el fallback (Tesseract) durante 60 segundos.
- **Reset**: Después de 60 segundos, se reintentar el proveedor primario automáticamente.

---

## Parsers compartidos

`ocr/parsers.py` contiene regex pre-compilados y funciones de parsing compartidas por todos los providers:

```python
from ocr.parsers import parsear_campos

resultado = parsear_campos(texto_ocr)
# {"cajero": "...", "fecha": "...", "hora": "...", "no_venta": "...", "monto": "...", "destinatario": "..."}
```

**Regex pre-compilados:**
- `RE_CAJERO` — detecta CAJERO, ATENDIO, VENDEDOR, EMPLEADO
- `RE_FECHA` — detecta fechas DD/MM/AAAA
- `RE_HORA` — detecta horas HH:MM
- `RE_VENTA` — detecta VENTA, TICKET, FOLIO
- `RE_MONTO` — detecta MONTO, TOTAL, IMPORTE
- `RE_DESTINATARIO` — detecta DESTINATARIO, PARA, BENEFICIARIO

---

## Cómo cambiar de proveedor

Editar `.env`:

```env
# Para Gemini (con fallback Tesseract automático)
OCR_PROVIDER=gemini

# Solo Tesseract local
OCR_PROVIDER=tesseract

# Solo OCR.space
OCR_PROVIDER=ocrspace
```

Reiniciar el servidor. Sin tocar código.

---

## Agregar un nuevo proveedor

1. Crear `ocr/nuevo_provider.py` heredando de `OCRProvider` (`ocr/base.py`)
2. Implementar `nombre` property + `extraer_campos(ruta) → OCRResult`
3. Registrar via `registrar_ocr("nombre", NuevoProvider)` en `ocr/__init__.py`
4. Agregar las claves/credenciales en `.env`
5. La factory valida automáticamente las keys al arrancar y emite warnings si faltan
6. Editar `PROVEEDORES_OCR.md` con la documentación

**Nota**: La factory usa registro dinámico (`_REGISTRO_OCR`), no un switch hardcodeado.
