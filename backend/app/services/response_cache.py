"""In-memory cache for repeat FAQ answers (skips RAG+LLM on cache hit)."""

from __future__ import annotations

import logging
import time

from app.core.config import Settings
from app.core.logging_config import wa_log

logger = logging.getLogger(__name__)


class ResponseCacheService:
    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.response_cache_enabled
        self._ttl = settings.response_cache_ttl_seconds
        self._memory: dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> str | None:
        if not self._enabled:
            return None
        t0 = time.perf_counter()
        entry = self._memory.get(key)
        if entry:
            text, expires = entry
            if time.time() < expires:
                wa_log(logger, "CACHE HIT", f"memory {time.perf_counter() - t0:.3f}s")
                return text
            del self._memory[key]
        return None

    def set(self, key: str, response: str) -> None:
        if not self._enabled or not response:
            return
        self._memory[key] = (response, time.time() + self._ttl)
