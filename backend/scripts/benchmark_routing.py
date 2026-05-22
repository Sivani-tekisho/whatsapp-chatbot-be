"""Compare RAG latency: routed namespaces vs searching all namespaces."""

import asyncio
import time

from app.core.config import get_settings
from app.dependencies import get_rag_service
from app.rag.query_router import route_query


QUERIES = [
    ("tekisho services", "services"),
    ("LeadQ pricing", "leadq"),  # product name wins over generic "pricing"
    ("hello how are you", None),
    ("What is VocalQ", "vocalq"),
]


async def main() -> None:
    settings = get_settings()
    rag = get_rag_service()
    configured = settings.pinecone_namespaces.split(",")

    print(f"Configured namespaces: {configured}")
    print("-" * 70)

    for query, expected_intent in QUERIES:
        route = route_query(query, configured)
        t0 = time.perf_counter()
        chunks = await asyncio.to_thread(rag.retrieve_context, query)
        elapsed = time.perf_counter() - t0
        match = "ok" if (expected_intent is None or route.intent == expected_intent) else "?"
        print(f"\nQuery: {query!r}")
        print(f"  Route intent:   {route.intent} [{match}]")
        print(f"  Namespaces:     {list(route.namespaces)} (count={route.namespace_count})")
        print(f"  Skip history:   {route.skip_chat_history}")
        print(f"  Embed preview:  {route.embed_query[:60]}...")
        print(f"  RAG time:       {elapsed:.2f}s  chunks={len(chunks)}")


if __name__ == "__main__":
    asyncio.run(main())
