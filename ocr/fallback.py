"""
fallback.py — Proveedor OCR con fallback automático y circuit breaker.

Prueba el proveedor primario (Gemini), y si falla (error de red,
cuota agotada, timeout, etc.) usa automáticamente el secundario (Tesseract).
Incluye circuit breaker que deshabilita temporalmente el primario tras N fallos.
"""

import time
import traceback

from config.logger import get_logger
from ocr.base import OCRProvider, OCRResult

logger = get_logger("fallback")


class CircuitBreaker:
    """Circuit breaker simple: tras N fallos consecutivos, bloquea por M segundos."""

    def __init__(self, max_fallos: int = 5, timeout_segundos: int = 60):
        self.max_fallos = max_fallos
        self.timeout_segundos = timeout_segundos
        self._fallos = 0
        self._bloqueado_hasta = 0.0

    @property
    def esta_abierto(self) -> bool:
        """Retorna True si el circuito está abierto (bloqueado)."""
        if self._fallos >= self.max_fallos:
            if time.time() < self._bloqueado_hasta:
                return True
            # Timeout expirado, resetear
            self._fallos = 0
            self._bloqueado_hasta = 0.0
        return False

    def registrar_exito(self):
        """Resetear contador de fallos."""
        self._fallos = 0
        self._bloqueado_hasta = 0.0

    def registrar_fallo(self):
        """Registrar un fallo y bloquear si se alcanza el máximo."""
        self._fallos += 1
        if self._fallos >= self.max_fallos:
            self._bloqueado_hasta = time.time() + self.timeout_segundos
            logger.warning(
                "Circuit breaker abierto — bloqueando proveedor por %ds tras %d fallos",
                self.timeout_segundos, self._fallos,
            )


class FallbackProvider(OCRProvider):
    """
    Envuelve dos proveedores: primario y fallback.

    extraer_campos() intenta con el primario. Si lanza cualquier excepción,
    registra el error completo y delega al fallback.
    Incluye circuit breaker para no repetir llamadas a APIs degradadas.
    """

    def __init__(self, primary: OCRProvider, fallback: OCRProvider):
        self._primary = primary
        self._fallback = fallback
        self._breaker = CircuitBreaker(max_fallos=5, timeout_segundos=60)

    @property
    def nombre(self) -> str:
        """Nombre compuesto: primario+fallback."""
        return f"{self._primary.nombre}+{self._fallback.nombre}"

    def extraer_campos(self, ruta_imagen: str) -> OCRResult:
        """Ejecuta el OCR con fallback y circuit breaker."""
        # Si el circuit breaker está abierto, ir directo al fallback
        if not self._breaker.esta_abierto:
            try:
                resultado = self._primary.extraer_campos(ruta_imagen)
                self._breaker.registrar_exito()
                return resultado
            except Exception as e:
                self._breaker.registrar_fallo()
                logger.warning(
                    "Fallback activado — %s falló, usando %s | error=%s",
                    self._primary.nombre,
                    self._fallback.nombre,
                    str(e)[:300],
                )
                logger.debug("Traceback:\n%s", traceback.format_exc())
        else:
            logger.info("Circuit breaker abierto — saltando %s", self._primary.nombre)

        return self._fallback.extraer_campos(ruta_imagen)
