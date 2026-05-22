"""Backward-compatible namespace helpers — logic lives in query_router."""

from __future__ import annotations

from app.rag.query_router import DEFAULT_NAMESPACE, route_query

PRODUCT_ALIASES: dict[str, list[str]] = {
    "leadq": ["leadq", "lead q", "lead-q", "lead q."],
    "vocalq": ["vocalq", "vocal q", "vocal-q", "vocal q."],
    "emailq": ["emailq", "email q", "email-q", "email q."],
}


def parse_namespace_list(raw: str) -> list[str]:
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
    return list(route_query(query, configured).namespaces)
