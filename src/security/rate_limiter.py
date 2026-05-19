"""
Rate Limiter — token bucket rate limiter for API calls.
"""

from __future__ import annotations
import asyncio
import time
from ..utils.config import get_config
from ..utils.logging_setup import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self) -> None:
        config = get_config()
        self._rpm = config.rate_limiting.requests_per_minute
        self._burst = config.rate_limiting.burst_size
        self._enabled = config.rate_limiting.enabled
        self._tokens = float(self._burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available."""
        if not self._enabled:
            return

        async with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

            # Wait for next token
            wait_time = (1.0 - self._tokens) / (self._rpm / 60.0)
            logger.debug("Rate limited — waiting %.1fs", wait_time)
            await asyncio.sleep(wait_time)
            self._refill()
            self._tokens -= 1.0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * (self._rpm / 60.0))
        self._last_refill = now
