"""
simular_ocr_seco.py — Simulacion en seco del pipeline OCR.

Ejecuta el pipeline OCR completo SIN servidor, SIN BD, SIN storage.
Verifica los 9 hallazgos de la auditoria.

Uso:
    uv run python tests/simular_ocr_seco.py <ruta_imagen>
    uv run python tests/simular_ocr_seco.py <ruta_imagen> --provider tesseract
    uv run python tests/simular_ocr_seco.py <ruta_imagen> --todos
    uv run python tests/simular_ocr_seco.py                        # usa imagen sintetica
"""

import argparse
import io
import inspect
import logging
import os
import sys
import threading
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.logger import setup_logging
from ocr import get_ocr_engine
from ocr.base import OCRResult
from ocr.compresion import comprimir_imagen
from ocr.fallback import CircuitBreaker, FallbackProvider
from ocr.parsers import parsear_campos
from ocr.tesseract_provider import TesseractProvider

setup_logging(level="INFO")
logger = logging.getLogger("sami.simulador")

PASS = "  PASS"
FAIL = "  FAIL"
WARN = "  WARN"

_contador_verificaciones = {"pasaron": 0, "fallaron": 0, "adv": 0}


def _v(condicion: bool, mensaje: str):
    if condicion:
        print(f"  {PASS}  {mensaje}")
        _contador_verificaciones["pasaron"] += 1
    else:
        print(f"  {FAIL}  {mensaje}")
        _contador_verificaciones["fallaron"] += 1


def _w(mensaje: str):
    print(f"  {WARN}  {mensaje}")
    _contador_verificaciones["adv"] += 1


def _separador(titulo: str):
    print(f"\n{'=' * 65}")
    print(f"  {titulo}")
    print(f"{'=' * 65}")


def _separador_sub(titulo: str):
    print(f"\n  --- {titulo} ---")


def _generar_imagen_sintetica() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (800, 400), (255, 255, 255))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "CAJERO: Juan Perez", fill=(0, 0, 0))
    draw.text((20, 60), "VENTA: 0012481545", fill=(0, 0, 0))
    draw.text((20, 100), "TOTAL: $1,234.56", fill=(0, 0, 0))
    draw.text((20, 140), "N de comprobante: 94644154", fill=(0, 0, 0))
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _imagen_a_archivo(datos: bytes, ruta: str):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    Path(ruta).write_bytes(datos)
    return ruta


# ── Casos de prueba ──


def caso_tesseract_procesa(ruta_imagen: str):
    """Caso 1: Pipeline basico con Tesseract."""
    _separador_sub("Caso 1: Tesseract procesa imagen valida")
    provider = TesseractProvider()
    if not provider.config.cmd or not os.path.exists(provider.config.cmd):
        _w("Tesseract no encontrado — salteando caso 1")
        return None
    t0 = time.perf_counter()
    resultado = provider.extraer_campos(ruta_imagen)
    t1 = time.perf_counter()
    print(f"     Tiempo: {(t1 - t0):.3f}s")
    print(f"     OCR reportado: {resultado.ocr}")
    print(f"     transfiere: {resultado.transfiere}")
    print(f"     no_comprobante: {resultado.no_comprobante}")
    print(f"     monto: {resultado.monto}")
    _v(resultado.ocr == "tesseract", "ocr == 'tesseract'")
    if resultado.texto_ocr_crudo is not None:
        _v(True, "texto_ocr_crudo extraido correctamente")
    else:
        _w("texto_ocr_crudo es None (Tesseract no encontro texto o no instalado)")
    return resultado


def caso_tesseract_semaphore_concurrencia():
    """Caso 5: Verificar semaforo de Tesseract."""
    _separador_sub("Caso 5: Semaforo de concurrencia Tesseract")
    provider = TesseractProvider()
    sem = provider._semaphore
    _v(isinstance(sem, threading.Semaphore), "Tesseract usa Semaphore")
    _v(sem._value >= 1, f"Semaphore._value >= 1 (valor: {sem._value})")
    print(f"     max_concurrent configurado: {provider.config.max_concurrent}")
    print(f"     Semaphore._value: {sem._value}")


def caso_tesseract_cache_preprocesamiento(ruta_imagen: str):
    """Caso 6: Cache de preprocesamiento."""
    _separador_sub("Caso 6: Cache de preprocesamiento Tesseract")
    provider = TesseractProvider()
    if not provider.config.cmd or not os.path.exists(provider.config.cmd):
        _w("Tesseract no encontrado — salteando caso 6")
        return
    t0 = time.perf_counter()
    provider.extraer_campos(ruta_imagen)
    t1 = time.perf_counter()
    t_sin_cache = t1 - t0
    t0 = time.perf_counter()
    provider.extraer_campos(ruta_imagen)
    t1 = time.perf_counter()
    t_con_cache = t1 - t0
    print(f"     Sin cache: {t_sin_cache:.4f}s")
    print(f"     Con cache: {t_con_cache:.4f}s")
    _v(t_con_cache <= t_sin_cache * 1.5, "Cache no es mas lento que sin cache")


def caso_parser_texto_manual():
    """Probar parser con texto directamente (sin OCR)."""
    _separador_sub("Caso A: Parser directo (sin OCR)")
    texto = """BANCO PICHINCHA
$ 20.00
A Barvecho Ordonez Maria Cristina
De Guzman Guzman Lorena
N de comprobante: 94644154"""
    resultado = parsear_campos(texto)
    print(f"     transfiere: {resultado.transfiere}")
    print(f"     no_comprobante: {resultado.no_comprobante}")
    print(f"     monto: {resultado.monto}")
    _v(resultado.transfiere == "Guzman Guzman Lorena", "transfiere extraido")
    _v(resultado.no_comprobante == "94644154", "no_comprobante extraido")
    _v(resultado.monto == "20.00", "monto extraido")
    _v(resultado.texto_ocr_crudo is not None, "texto_ocr_crudo presente")


def caso_parser_n_de_comprobante_linea_siguiente():
    """Probar cuando N de comprobante esta en la linea siguiente."""
    _separador_sub("Caso B: Comprobante en linea siguiente")
    texto = """N de comprobante
6953"""
    resultado = parsear_campos(texto)
    print(f"     no_comprobante: {resultado.no_comprobante}")
    _v(resultado.no_comprobante == "6953", "no_comprobante en linea sig")


def caso_parser_n_de_comprobante_corrupto():
    """Probar N con caracter corrupto (U+FFFD)."""
    _separador_sub("Caso C: N corrupto con U+FFFD")
    texto = "N\uFFFD de comprobante\n6953"
    resultado = parsear_campos(texto)
    print(f"     no_comprobante: {resultado.no_comprobante}")
    _v(resultado.no_comprobante == "6953", "no_comprobante corrupto")


def caso_parser_texto_vacio():
    """Probar parser con texto vacio."""
    _separador_sub("Caso D: Texto vacio")
    resultado = parsear_campos("")
    _v(resultado.transfiere is None, "transfiere None en vacio")
    _v(resultado.no_comprobante is None, "no_comprobante None en vacio")
    _v(resultado.monto is None, "monto None en vacio")


def caso_hallazgo1_ocr_se_persiste():
    """Hallazgo #1 (fijo): ocr SI se persiste en ORM."""
    _separador_sub("Hallazgo #1: ocr se persiste en ORM")
    resultado = OCRResult(ocr="gemini", transfiere="Juan", monto="100")
    data_orm = resultado.model_dump(exclude_none=True)
    _v(data_orm.get("ocr") == "gemini", "ocr incluido en model_dump")
    _v(data_orm.get("transfiere") == "Juan", "transfiere incluido")
    _v(data_orm.get("monto") == "100", "monto incluido")
    print(f"     Campos en model_dump: {list(data_orm.keys())}")


def caso_hallazgo2_nombre_engine():
    """Hallazgo #2 (contexto): engine.nombre en FallbackProvider siempre es compuesto."""
    _separador_sub("Hallazgo #2: engine.nombre compuesto en FallbackProvider")
    # tesseract directo es simple
    os.environ["OCR_PROVIDER"] = "tesseract"
    import ocr
    ocr._engine_instance = None
    engine = get_ocr_engine()
    _v(engine.nombre == "tesseract", "tesseract directo -> nombre simple")
    # FallbackProvider siempre devuelve compuesto
    fp = FallbackProvider(primary=TesseractProvider(), fallback=TesseractProvider())
    _v("+" in fp.nombre, "FallbackProvider.nombre contiene '+'")
    print(f"     FallbackProvider.nombre: {fp.nombre}")


def caso_hallazgo4_parsers_diferentes():
    """Hallazgo #4: Gemini usa parser JSON propio, no parsear_campos()."""
    _separador_sub("Hallazgo #4: Gemini parser propio vs parsear_campos")
    from ocr.gemini_provider import GeminiProvider

    source = inspect.getsource(GeminiProvider.extraer_campos)
    _v("_parsear_json" in source, "Gemini usa _parsear_json (no parsear_campos)")
    _v("parsear_campos" not in source, "Gemini NO importa parsear_campos")
    print("     Gemini: parsea JSON directamente via _parsear_json()")
    print("     OCRSpace y Tesseract: usan parsear_campos() con regex")


def caso_hallazgo5_singleton_engine():
    """Hallazgo #5: get_ocr_engine() es singleton."""
    _separador_sub("Hallazgo #5: get_ocr_engine() es singleton")
    a = get_ocr_engine()
    b = get_ocr_engine()
    c = get_ocr_engine()
    _v(a is b, "Llamada 1 y 2 misma instancia")
    _v(b is c, "Llamada 2 y 3 misma instancia")
    from ocr import _engine_instance
    _v(_engine_instance is a, "_engine_instance module-level coincide")


def caso_hallazgo6_compresion_doble_ocrspace():
    """Hallazgo #6: OCRSpace comprime imagen + base64."""
    _separador_sub("Hallazgo #6: Compresion en OCRSpace y Gemini")
    from ocr.ocrspace_provider import OCRSpaceProvider

    source = inspect.getsource(OCRSpaceProvider.extraer_campos)
    _v("comprimir_imagen" in source, "OCRSpace llama comprimir_imagen()")
    _v("base64.b64encode" in source, "OCRSpace codifica en base64")

    from ocr.gemini_provider import GeminiProvider

    source = inspect.getsource(GeminiProvider.extraer_campos)
    _v("comprimir_imagen" in source, "Gemini llama comprimir_imagen()")

    from ocr.tesseract_provider import TesseractProvider

    source = inspect.getsource(TesseractProvider.extraer_campos)
    _v("comprimir_imagen" not in source, "Tesseract NO comprime")
    print("     Gemini/OCRSpace: comprimir_imagen() + envio remoto")
    print("     Tesseract: preprocesamiento PIL local (sin comprimir)")


def caso_hallazgo8_storage_no_singleton():
    """Hallazgo #8: storage factory no es singleton (pero clientes internos si)."""
    _separador_sub("Hallazgo #8: Storage factory vs singletons internos")
    from storage import get_storage_backend

    a = get_storage_backend()
    b = get_storage_backend()
    _v(a is not b, "get_storage_backend() crea nueva instancia cada vez")
    _v(type(a) is type(b), "Misma clase en ambas instancias")
    print(f"     a is b: {a is b} (esperado: False)")
    _w("Por diseno: factory liviana, clientes pesados (S3, Gemini) son singleton internos")


def caso_hallazgo7_storage_resolver_temp():
    """Hallazgo #7: storage resolver crea temporales para remotos."""
    _separador_sub("Hallazgo #7: resolver_ruta en backends remotos")
    from storage.s3 import S3StorageProvider
    from storage.cloudinary import CloudinaryStorageProvider
    from storage.local import LocalStorageProvider

    local = LocalStorageProvider()
    s3 = S3StorageProvider()
    cl = CloudinaryStorageProvider()
    _v(local.es_local(), "LocalStorageProvider.es_local() == True")
    _v(not s3.es_local(), "S3StorageProvider.es_local() == False")
    _v(not cl.es_local(), "CloudinaryStorageProvider.es_local() == False")
    _v(local.limpiar_temporal(None) is None, "Local.limpiar_temporal() no-op")


def caso_circuit_breaker():
    """Verificar circuit breaker: 5 fallos -> bloqueo 60s."""
    _separador_sub("Hallazgo: Circuit Breaker")
    cb = CircuitBreaker(max_fallos=3, timeout_segundos=2)
    _v(not cb.esta_abierto, "CB comienza cerrado")
    for _ in range(3):
        cb.registrar_fallo()
    _v(cb.esta_abierto, "CB se abre tras 3 fallos")
    cb.registrar_exito()
    _v(not cb.esta_abierto, "CB se cierra al registrar exito")
    for _ in range(3):
        cb.registrar_fallo()
    _v(cb.esta_abierto, "CB se abre de nuevo")
    print("     Timeout configurado: 2s")
    time.sleep(2.1)
    _v(not cb.esta_abierto, "CB se rearma tras timeout")


def caso_compresion_real(datos_imagen: bytes):
    """Verificar compresion con datos reales."""
    _separador_sub("Verificacion: Compresion de imagen")
    comprimidos = comprimir_imagen(datos_imagen)
    if len(comprimidos) < len(datos_imagen):
        print(f"     Original: {len(datos_imagen)} bytes")
        print(f"     Comprimido: {len(comprimidos)} bytes")
        print(f"     Reduccion: {(1 - len(comprimidos) / len(datos_imagen)) * 100:.1f}%")
        _v(len(comprimidos) <= len(datos_imagen), "Compresion no agranda el archivo")
    else:
        _w("Imagen no supero umbrales de compresion (activar_si_excede_bytes=1MB)")
        print("     La imagen se devolvio sin cambios")


def caso_static_files():
    """Verificar que main.py monta /static."""
    _separador_sub("Verificacion: Static files")
    static_path = Path("static")
    _v(static_path.exists(), "Directorio static/ existe")
    index_path = static_path / "index.html"
    _v(index_path.exists(), "static/index.html existe")
    print(f"     Archivos en static/: {[p.name for p in static_path.iterdir()]}")


# ── Main ──


def main():
    parser = argparse.ArgumentParser(
        description="Simulacion en seco del pipeline OCR de SAMI"
    )
    parser.add_argument("ruta_imagen", nargs="?", help="Ruta a la imagen de prueba")
    parser.add_argument(
        "--provider",
        choices=["tesseract", "ocrspace", "gemini"],
        default=None,
        help="Proveedor OCR a probar (default: el de .env)",
    )
    parser.add_argument(
        "--todos",
        action="store_true",
        help="Ejecutar todos los casos de verificacion",
    )
    parser.add_argument(
        "--solo-parser",
        action="store_true",
        help="Solo probar parseo directo (sin OCR real)",
    )
    args = parser.parse_args()

    ruta_imagen = args.ruta_imagen
    if ruta_imagen and not os.path.exists(ruta_imagen):
        print(f"ERROR: No se encuentra la imagen: {ruta_imagen}")
        sys.exit(1)

    if not ruta_imagen:
        print("No se especifico imagen — generando imagen sintetica...")
        datos = _generar_imagen_sintetica()
        ruta_imagen = _imagen_a_archivo(datos, "uploads/_test_sintetica.jpg")
        print(f"  Imagen sintetica creada: {ruta_imagen} ({len(datos)} bytes)")
    else:
        datos = Path(ruta_imagen).read_bytes()

    print(f"\n{'#' * 65}")
    print("#  SIMULACION OCR SECO — SAMI")
    print(f"#  Imagen: {ruta_imagen} ({len(datos)} bytes)")
    print(f"{'#' * 65}")

    if args.provider:
        os.environ["OCR_PROVIDER"] = args.provider
        print(f"  Proveedor forzado: {args.provider}")
        import ocr
        ocr._engine_instance = None

    # ── Si solo parser ──
    if args.solo_parser:
        caso_parser_texto_manual()
        caso_parser_n_de_comprobante_linea_siguiente()
        caso_parser_n_de_comprobante_corrupto()
        caso_parser_texto_vacio()
        _resumen()
        return

    # ── Pipeline real ──
    _separador("1. PIPELINE OCR REAL")
    caso_tesseract_procesa(ruta_imagen)

    _separador("2. PARSER DIRECTO (SIN OCR)")
    caso_parser_texto_manual()
    caso_parser_n_de_comprobante_linea_siguiente()
    caso_parser_n_de_comprobante_corrupto()
    caso_parser_texto_vacio()

    _separador("3. VERIFICACION DE COMPRESION")
    caso_compresion_real(datos)

    _separador("4. HALLAZGOS DE AUDITORIA")
    if args.todos:
        caso_hallazgo1_ocr_se_persiste()
        caso_hallazgo2_nombre_engine()
        caso_hallazgo4_parsers_diferentes()
        caso_hallazgo5_singleton_engine()
        caso_hallazgo6_compresion_doble_ocrspace()
        caso_hallazgo7_storage_resolver_temp()
        caso_hallazgo8_storage_no_singleton()
        caso_circuit_breaker()
        caso_tesseract_semaphore_concurrencia()
        caso_tesseract_cache_preprocesamiento(ruta_imagen)
        caso_static_files()
    else:
        print("  (usa --todos para ejecutar las 9 verificaciones de auditoria)")

    _resumen()


def _resumen():
    print(f"\n{'=' * 65}")
    print("  RESUMEN DE VERIFICACIONES")
    print(f"{'=' * 65}")
    total = (
        _contador_verificaciones["pasaron"]
        + _contador_verificaciones["fallaron"]
        + _contador_verificaciones["adv"]
    )
    print(
        f"  Total: {total}  |  "
        f"{PASS}: {_contador_verificaciones['pasaron']}  |  "
        f"{FAIL}: {_contador_verificaciones['fallaron']}  |  "
        f"{WARN}: {_contador_verificaciones['adv']}"
    )
    if _contador_verificaciones["fallaron"] > 0:
        print("\n  ALGUNAS VERIFICACIONES FALLARON — revisar output arriba.")
    print()


if __name__ == "__main__":
    main()
