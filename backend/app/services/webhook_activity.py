"""In-memory webhook activity (survives until server restart)."""

from collections import deque
from datetime import datetime, timezone

_MAX = 30
_events: deque[dict] = deque(maxlen=_MAX)
_meta_verified_at: str | None = None
_last_post_at: str | None = None
_last_post_phone: str | None = None
_whatsapp_message_count: int = 0


def log_event(method: str, detail: str, phone: str | None = None) -> None:
    global _meta_verified_at, _last_post_at, _last_post_phone, _whatsapp_message_count

    now = datetime.now(timezone.utc).isoformat()
    _events.appendleft(
        {
            "time": now,
            "method": method,
            "detail": detail,
            "phone": phone,
        }
    )

    if method == "GET" and "verification OK" in detail:
        _meta_verified_at = now
    if method == "POST" and phone:
        _last_post_at = now
        _last_post_phone = phone
        _whatsapp_message_count += 1


def get_recent_events() -> list[dict]:
    return list(_events)


def get_summary() -> dict:
    return {
        "meta_verified": _meta_verified_at is not None,
        "meta_verified_at": _meta_verified_at,
        "whatsapp_connected": _whatsapp_message_count > 0,
        "whatsapp_message_count": _whatsapp_message_count,
        "last_whatsapp_post_at": _last_post_at,
        "last_whatsapp_phone": _last_post_phone,
        "recent_events": get_recent_events(),
    }
