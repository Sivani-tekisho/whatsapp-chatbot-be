"""Optional RAG chunk filtering (disabled by default — use only retrieved context)."""

from __future__ import annotations

import re

# When enabled via RAG_FILTER_OFF_TOPIC=true, drop obvious wrong-industry chunks
# that lack any company/product mention (reduces healthcare/logistics noise in index).
_COMPANY_MARKERS = frozenset(
    {
        "tekisho",
        "leadq",
        "vocalq",
        "emailq",
        "tekisho.ai",
        "tekisho infotech",
    }
)

_OFF_TOPIC_VERTICALS = frozenset(
    {
        "transportation & logistics",
        "fall & incident detection",
        "occupancy analytics",
        "cargo tracking",
    }
)

_PRODUCT_PREFIX = re.compile(r"^\[(leadq|vocalq|emailq)\]\s", re.I)


def chunk_is_on_topic(text: str) -> bool:
    if not text or not text.strip():
        return False
    t = text.lower().strip()
    if _PRODUCT_PREFIX.match(t):
        return True
    has_company = any(m in t for m in _COMPANY_MARKERS)
    has_vertical = any(v in t for v in _OFF_TOPIC_VERTICALS)
    if has_vertical and not has_company:
        return False
    return True


def filter_company_chunks(chunks: list[str], *, enabled: bool) -> list[str]:
    if not enabled:
        return chunks
    return [c for c in chunks if chunk_is_on_topic(c)]
