"""
test_rate_limiter.py — Tests de rate limiting.
"""

from utils.rate_limiter import RateLimiter


def test_rate_limiter_permite_primer_request():
    rl = RateLimiter(max_requests=5, window_seconds=60)
    assert rl.permitir("192.168.1.1") is True


def test_rate_limiter_permite_varios_dentro_limite():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    assert rl.permitir("192.168.1.1") is True
    assert rl.permitir("192.168.1.1") is True
    assert rl.permitir("192.168.1.1") is True


def test_rate_limiter_bloquea_exceso():
    rl = RateLimiter(max_requests=2, window_seconds=60)
    rl.permitir("192.168.1.1")
    rl.permitir("192.168.1.1")
    assert rl.permitir("192.168.1.1") is False


def test_rate_limiter_independiente_por_ip():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    rl.permitir("192.168.1.1")
    assert rl.permitir("192.168.1.2") is True
