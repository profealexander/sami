# SAMI - Sistema de Archivo y Manejo de Imagenes de Comprobantes

> Captura de comprobantes desde el telefono, OCR multi-proveedor y almacenamiento local.
> **v2.0.0** - Multi-tenant, configurable por entorno, despliegue flexible.

---

## Arquitectura (3 capas + infraestructura)

```
Capa 1:  main.py              Controlador FastAPI (rutas, CORS, PWA)
Capa 2:  service.py           Logica de negocio (OCR + almacenamiento + BD)
Capa 3:  database/            Repositorio SQLite / PostgreSQL (backend intercambiable)

Infra:   config/              server.py + settings.py (entorno, BD, storage)
         ocr/                 Motores OCR intercambiables (gemini, tesseract, ocrspace)
         run.py               Entry point unico
```

Cada capa documenta su arquitectura interna en su propio README:
- `database/README.md` — Motores de BD, modelos, como anadir uno nuevo
- `ocr/PROVEEDORES_OCR.md` — Proveedores OCR, configuracion, fallback

---

## Proveedores OCR

| Proveedor | Variable .env | Tipo | Limite gratis |
|---|---|---|---|
| Google Gemini | OCR_PROVIDER=gemini | API cloud (IA) | 1,500 req/dia |
| Tesseract | OCR_PROVIDER=tesseract | Local (sin internet) | Ilimitado |
| OCR.space | OCR_PROVIDER=ocrspace | API cloud | 25,000 req/mes |

**gemini** es el principal. Si falla (cuota agotada, sin internet) **cae automaticamente a Tesseract** como fallback local.
Cada proveedor tiene su propia config en ocr/*_provider.py con parametros desde .env.

Documentacion detallada en: `ocr/PROVEEDORES_OCR.md`

---

## Entornos

| Entorno | Uso | Comando |
|---|---|---|
| development | Local (tu PC, pendrive) | `python run.py` |
| production | VPS / Railway / Render | `ENV=production python run.py` |

Diferencia: produccion usa mas workers, sin reload, logs minimos, CORS restringido.

---

## Variables de entorno (.env)

### Entorno y servidor
| Variable | Descripcion | Default |
|---|---|---|
| ENV | development o production | development |
| HOST | IP del servidor | 0.0.0.0 |
| PORT | Puerto | 8000 |
| WORKERS | Workers (4 en prod, 1 en dev) | auto |
| RELOAD | Hot-reload (solo dev) | auto |
| LOG_LEVEL | info / warning / error | auto |
| CORS_ORIGINS | Origenes permitidos (* o lista) | * |

### Base de datos
| Variable | Descripcion | Default |
|---|---|---|
| DATABASE_URL | sqlite:///... o postgresql://... | sqlite:///./comprobantes.db |
| DB_POOL_SIZE | Pool de conexiones PostgreSQL | 10 |

### Almacenamiento
| Variable | Descripcion | Default |
|---|---|---|
| STORAGE_BACKEND | local / s3 / cloudinary | local |
| S3_BUCKET | Bucket S3 | - |
| S3_REGION | Region AWS | - |
| S3_ACCESS_KEY | Access key S3 | - |
| S3_SECRET_KEY | Secret key S3 | - |
| CLOUDINARY_URL | URL Cloudinary | - |

---

## Instalacion

```bash
uv sync
python run.py
# http://localhost:7000
```

Para produccion con PostgreSQL:
```bash
docker compose up -d
```

---

## Endpoints

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | / | Frontend PWA |
| GET | /docs | Documentacion Swagger |
| POST | /api/upload | Sube imagen + cliente_id |

---

## Despliegue

### Local (hoy)
```bash
python run.py
ngrok http 7000
# El celular se connecta via Ngrok
```

### VPS / Railway / Render
```bash
ENV=production DATABASE_URL=postgresql://... python run.py
```

### Docker
```bash
docker compose up -d
```

### GitHub -> Render/Koyeb
Conectar repo, Render detecta Procfile automaticamente.
Variables de entorno se configuran en el dashboard de Render/Koyeb.
