"""Cache keys and intent — uses central query_router."""

from __future__ import annotations

import hashlib

from app.rag.query_router import detect_intent, normalize_query

# Re-export for callers
__all__ = [
    "normalize_query",
    "detect_intent_bucket",
    "cache_key_for_message",
]

detect_intent_bucket = detect_intent


def cache_key_for_message(
    text: str, organization_id: str, company_name: str = ""
) -> str:
    co = normalize_query(company_name) or "company"
    bucket = detect_intent(text)
    if bucket:
        payload = f"{co}:{bucket}"
    else:
        norm = normalize_query(text)
        digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:32]
        payload = f"{co}:{digest}"
    return f"wa:reply:{organization_id}:{payload}"
