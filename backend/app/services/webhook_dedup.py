"""In-memory deduplication for Meta webhook message IDs (survives until process restart)."""

from collections import OrderedDict
from threading import Lock

_MAX_IDS = 5000
_seen: OrderedDict[str, None] = OrderedDict()
_lock = Lock()


def is_duplicate_message(message_id: str | None) -> bool:
    """Return True if this WhatsApp message_id was already processed."""
    if not message_id:
        return False
    with _lock:
        if message_id in _seen:
            return True
        _seen[message_id] = None
        while len(_seen) > _MAX_IDS:
            _seen.popitem(last=False)
        return False
