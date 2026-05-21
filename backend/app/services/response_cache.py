"""Response cache for LLM replies.

Caches bot replies keyed by normalised message text so identical (or near-identical)
questions skip the LLM on repeat asks.

- TTL  : 3600 s (1 hour)
- Size : 1 000 entries
- Skip : replies containing personalisation signals are never cached
"""

import hashlib
import re

from cachetools import TTLCache

_response_cache: TTLCache = TTLCache(maxsize=1000, ttl=3600)

# Replies that reference conversation-specific context must NOT be cached
_PERSONALISATION_SIGNALS: tuple[str, ...] = (
    "your name",
    "you told me",
    "earlier you",
    "last time",
    "previously",
    "as you said",
    "you mentioned",
)

_PUNCT_RE = re.compile(r"[^\w\s]")
_SPACE_RE = re.compile(r"\s+")


def make_cache_key(message: str) -> str:
    """Normalise message and return its MD5 hex digest as cache key."""
    normalised = message.lower().strip()
    normalised = _PUNCT_RE.sub("", normalised)
    normalised = _SPACE_RE.sub(" ", normalised).strip()
    return hashlib.md5(normalised.encode()).hexdigest()


async def get_cached_response(message: str) -> str | None:
    """Return a cached reply for *message*, or None if not cached."""
    key = make_cache_key(message)
    return _response_cache.get(key)


async def set_cached_response(message: str, reply: str) -> None:
    """Cache *reply* for *message* unless the reply is personalised."""
    reply_lower = reply.lower()
    if any(signal in reply_lower for signal in _PERSONALISATION_SIGNALS):
        return
    key = make_cache_key(message)
    _response_cache[key] = reply


async def invalidate_cache(message: str) -> None:
    """Remove a specific message from the response cache."""
    key = make_cache_key(message)
    _response_cache.pop(key, None)
