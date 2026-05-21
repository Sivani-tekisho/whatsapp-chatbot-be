"""Shared in-memory TTLCache instances.

All caches are module-level singletons — one instance per worker process.
TTL = 600 seconds (10 minutes) for all caches.

Usage:
    from app.cache import org_cache, rag_cache, embedding_cache, cache_get, cache_set
"""

import threading
from cachetools import TTLCache

_TTL = 600          # 10 minutes
_LOCK = threading.Lock()

# ── org / company settings (fetched from Supabase organizations table) ────────
org_cache: TTLCache = TTLCache(maxsize=64, ttl=_TTL)

# ── RAG chunk results  key: query_text  value: list[str] ─────────────────────
rag_cache: TTLCache = TTLCache(maxsize=256, ttl=_TTL)

# ── OpenAI embedding vectors  key: text  value: list[float] ──────────────────
embedding_cache: TTLCache = TTLCache(maxsize=512, ttl=_TTL)


# ── Fully-built prompt strings (avoid rebuilding identical prompts) ──────────
prompt_cache: TTLCache = TTLCache(maxsize=200, ttl=300)     # 5 min TTL

# ── Pinecone results keyed by embedding hash (skip identical vector queries) ─
rag_result_cache: TTLCache = TTLCache(maxsize=500, ttl=600)  # 10 min TTL


def cache_get(cache: TTLCache, key: str) -> tuple[bool, object]:
    """Thread-safe get.  Returns (hit: bool, value)."""
    with _LOCK:
        if key in cache:
            return True, cache[key]
    return False, None


def cache_set(cache: TTLCache, key: str, value: object) -> None:
    """Thread-safe set."""
    with _LOCK:
        cache[key] = value
