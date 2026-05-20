"""Map user queries to Pinecone namespaces (Tekisho + product lines)."""

from __future__ import annotations

DEFAULT_NAMESPACE = "__default__"

# Namespace name in Pinecone → phrases that indicate the user means this product
PRODUCT_ALIASES: dict[str, list[str]] = {
    "leadq": ["leadq", "lead q", "lead-q", "lead q."],
    "vocalq": ["vocalq", "vocal q", "vocal-q", "vocal q."],
    "emailq": ["emailq", "email q", "email-q", "email q."],
}


def parse_namespace_list(raw: str) -> list[str]:
    """Comma-separated env value → ordered unique namespace names."""
    if not raw or not raw.strip():
        return []
    seen: set[str] = set()
    out: list[str] = []
    for part in raw.split(","):
        name = part.strip()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def namespaces_for_query(query: str, configured: list[str]) -> list[str]:
    """
    Choose which Pinecone namespaces to search.

    - Product mentioned (leadq, vocalq, emailq) → that namespace(s) + __default__
    - General / Tekisho questions → __default__ only (existing behaviour)
    """
    if not configured:
        return [DEFAULT_NAMESPACE]

    available = set(configured)
    q = query.lower()
    matched: list[str] = []

    for ns, aliases in PRODUCT_ALIASES.items():
        if ns not in available:
            continue
        if any(alias in q for alias in aliases):
            matched.append(ns)

    if matched:
        ordered: list[str] = []
        for ns in matched:
            if ns not in ordered:
                ordered.append(ns)
        if DEFAULT_NAMESPACE in available and DEFAULT_NAMESPACE not in ordered:
            ordered.append(DEFAULT_NAMESPACE)
        return ordered

    if DEFAULT_NAMESPACE in available:
        return [DEFAULT_NAMESPACE]

    return configured
