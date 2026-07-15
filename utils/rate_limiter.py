"""
rate_limiter.py — Rate limiting simple por IP.
"""

import time
from collections import defaultdict


class RateLimiter:
    """Rate limiter basado en ventana deslizante."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def permitir(self, key: str) -> bool:
        """Retorna True si el request está dentro del límite."""
        ahora = time.time()
        ventana = ahora - self.window_seconds
        # Limpiar requests fuera de la ventana
        self._requests[key] = [t for t in self._requests[key] if t > ventana]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(ahora)
        return True
