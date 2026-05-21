"""Conversation memory / history loading — with in-process LRU cache.

Each conversation keeps its last N messages in RAM so we skip a Supabase
round-trip on every bot reply. The cache is kept in sync whenever a new
message is saved via append_to_cache().
"""

import logging
import threading
from collections import OrderedDict
from uuid import UUID

from supabase import Client

from app.core.config import Settings
from app.core.logging_config import wa_log

logger = logging.getLogger(__name__)

# ── module-level LRU cache shared across all MemoryService instances ──────────
# key: str(conversation_id)  value: list[{role, message}] (chronological order)
_CACHE: OrderedDict[str, list[dict]] = OrderedDict()
_CACHE_LOCK = threading.Lock()
_MAX_CONVERSATIONS = 500   # evict oldest conversation when limit is hit


def _cache_get(conv_id: str) -> list[dict] | None:
    with _CACHE_LOCK:
        if conv_id in _CACHE:
            _CACHE.move_to_end(conv_id)       # mark as recently used
            return list(_CACHE[conv_id])       # return a copy
    return None


def _cache_set(conv_id: str, messages: list[dict]) -> None:
    with _CACHE_LOCK:
        _CACHE[conv_id] = list(messages)
        _CACHE.move_to_end(conv_id)
        if len(_CACHE) > _MAX_CONVERSATIONS:
            _CACHE.popitem(last=False)          # evict least-recently-used


def _cache_append(conv_id: str, role: str, message: str, limit: int) -> None:
    """Append one message to the cache entry and trim to limit."""
    with _CACHE_LOCK:
        entry = list(_CACHE.get(conv_id, []))
        entry.append({"role": role, "message": message})
        if limit > 0:
            entry = entry[-limit:]
        _CACHE[conv_id] = entry
        _CACHE.move_to_end(conv_id)


class MemoryService:
    def __init__(self, db: Client, settings: Settings) -> None:
        self._db = db
        # Always keep at least 10 messages; respect explicit config if higher
        self._limit = max(settings.conversation_history_limit, 10)

    def load_history(self, conversation_id: UUID) -> list[dict]:
        """Return last N messages in chronological order for LLM context.

        Served from RAM on cache hit — no Supabase query needed.
        """
        conv_id = str(conversation_id)

        cached = _cache_get(conv_id)
        if cached is not None:
            return cached

        # Cache miss → fetch from Supabase once, then warm the cache
        rows = (
            self._db.table("messages")
            .select("role, message")
            .eq("conversation_id", conv_id)
            .order("timestamp", desc=True)
            .limit(self._limit)
            .execute()
            .data
            or []
        )
        rows = list(reversed(rows))
        history = [
            {"role": r["role"], "message": r["message"]}
            for r in rows
            if r["role"] != "system"
        ]
        _cache_set(conv_id, history)
        wa_log(logger, "MEMORY", f"Loaded {len(history)} turns for convo {conversation_id}")
        return history

    def append_to_cache(self, conversation_id: UUID, role: str, message: str) -> None:
        """Keep RAM cache in sync after save_message() persists to Supabase."""
        if role == "system":
            return
        _cache_append(str(conversation_id), role, message, self._limit)

    def invalidate(self, conversation_id: UUID) -> None:
        """Force next load_history() to re-fetch from Supabase."""
        with _CACHE_LOCK:
            _CACHE.pop(str(conversation_id), None)
