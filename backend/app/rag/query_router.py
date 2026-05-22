"""
Route user messages to the right Pinecone namespace(s) and optimized DB/RAG behavior.

- Intent detection (services, pricing, leadq, …)
- Namespace selection (search 1 namespace instead of 4 when possible)
- Embedding query expansion (better retrieval without extra LLM calls)
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_NAMESPACE = "__default__"

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

# Intent → namespaces to query (order matters: product first, then company default)
_INTENT_NAMESPACES: dict[str, list[str]] = {
    "leadq": ["leadq", DEFAULT_NAMESPACE],
    "vocalq": ["vocalq", DEFAULT_NAMESPACE],
    "emailq": ["emailq", DEFAULT_NAMESPACE],
    "services": [DEFAULT_NAMESPACE],
    "pricing": [DEFAULT_NAMESPACE],
    "contact": [DEFAULT_NAMESPACE],
    "about": [DEFAULT_NAMESPACE],
    "signup": [DEFAULT_NAMESPACE],
    "trial": [DEFAULT_NAMESPACE],
    "demo": [DEFAULT_NAMESPACE],
    "hours": [DEFAULT_NAMESPACE],
}

# Keyword groups → intent label for routing, cache keys, and {{DETECTED_INTENT}} in prompts
_INTENT_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("sign up", "signup", "sign-up", "register", "registration", "get started", "onboarding"), "signup"),
    (("free trial", "free trail", "trial", "pilot"), "trial"),
    (("demo", "book a call", "schedule", "meeting"), "demo"),
    (("business hours", "working hours", "office hours", "open", "timing"), "hours"),
    (("service", "services"), "services"),
    (("price", "pricing", "cost", "plan", "plans"), "pricing"),
    (("contact", "email", "phone", "call", "reach", "whatsapp"), "contact"),
    (("about", "who are you", "company"), "about"),
    (("leadq", "lead q"), "leadq"),
    (("vocalq", "vocal q"), "vocalq"),
    (("emailq", "email q"), "emailq"),
]

# Intents that are standalone FAQ — skip loading chat history
_SKIP_HISTORY_INTENTS = frozenset(
    {
        "services",
        "pricing",
        "contact",
        "about",
        "signup",
        "trial",
        "demo",
        "hours",
        "leadq",
        "vocalq",
        "emailq",
    }
)


@dataclass(frozen=True)
class QueryRoute:
    """Result of routing one user message."""

    raw_query: str
    intent: str | None
    namespaces: tuple[str, ...]
    embed_query: str
    skip_chat_history: bool

    @property
    def namespace_count(self) -> int:
        return len(self.namespaces)


def normalize_query(text: str) -> str:
    import re

    t = (text or "").lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def detect_intent(query: str) -> str | None:
    norm = normalize_query(query)
    if not norm:
        return None
    product = _detect_product_intent(norm)
    if product:
        return product
    for keywords, intent in _INTENT_KEYWORDS:
        if any(kw in norm for kw in keywords):
            return intent
    return None


def _detect_product_intent(norm: str) -> str | None:
    for ns, aliases in PRODUCT_ALIASES.items():
        if any(alias.replace(" ", "") in norm.replace(" ", "") or alias in norm for alias in aliases):
            return ns
    return None


def _resolve_namespaces(intent: str | None, configured: list[str]) -> list[str]:
    available = set(configured) if configured else {DEFAULT_NAMESPACE}
    if not intent or intent not in _INTENT_NAMESPACES:
        if DEFAULT_NAMESPACE in available:
            return [DEFAULT_NAMESPACE]
        return list(configured)[:1] if configured else [DEFAULT_NAMESPACE]

    wanted = _INTENT_NAMESPACES[intent]
    resolved: list[str] = []
    for ns in wanted:
        if ns in available and ns not in resolved:
            resolved.append(ns)
    if resolved:
        return resolved
    if DEFAULT_NAMESPACE in available:
        return [DEFAULT_NAMESPACE]
    return list(configured)[:1]


def build_embed_query(raw_query: str, intent: str | None) -> str:
    """Use the user's words for vector search — no hardcoded embed strings in code."""
    del intent
    return raw_query.strip()


def route_query(query: str, configured_namespaces: list[str] | str | None = None) -> QueryRoute:
    """
    Full routing decision for one user message.

    configured_namespaces: list or comma-separated env string.
    """
    if isinstance(configured_namespaces, str):
        configured = parse_namespace_list(configured_namespaces)
    else:
        configured = list(configured_namespaces or [])

    raw = (query or "").strip()
    intent = detect_intent(raw)
    namespaces = _resolve_namespaces(intent, configured)
    embed = build_embed_query(raw, intent)
    skip_history = intent in _SKIP_HISTORY_INTENTS

    return QueryRoute(
        raw_query=raw,
        intent=intent,
        namespaces=tuple(namespaces),
        embed_query=embed,
        skip_chat_history=skip_history,
    )
