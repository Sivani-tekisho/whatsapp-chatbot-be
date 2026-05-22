"""Time each step of the reply pipeline. Run: python scripts/benchmark_latency.py"""

import asyncio
import time
import uuid

from app.core.config import get_settings
from app.dependencies import get_company_agent, get_rag_service
from app.services.response_cache import ResponseCacheService


async def main() -> None:
    settings = get_settings()
    agent = get_company_agent()
    rag = get_rag_service()
    cache = ResponseCacheService(settings)

    queries = [
        "What are Tekisho services?",
        "What are Tekisho services?",  # repeat — should hit cache
        "tekisho services",
    ]

    fake_conv_id = uuid.uuid4()
    org = {
        "id": settings.default_organization_id,
        "name": "Tekisho Infotech",
        "fallback_message": "I couldn't find that information.",
        "greeting_message": "Hello! How can I help you today?",
    }

    print(f"model={settings.openai_model} top_k={settings.rag_top_k} history_limit={settings.conversation_history_limit}")
    print("-" * 60)

    for i, q in enumerate(queries):
        print(f"\n[{i + 1}] Query: {q!r}")

        t0 = time.perf_counter()
        t_rag = time.perf_counter()
        chunks = await asyncio.to_thread(rag.retrieve_context, q)
        rag_s = time.perf_counter() - t_rag
        print(f"  RAG only:        {rag_s:.2f}s  chunks={len(chunks)}")

        t_llm = time.perf_counter()
        try:
            out = await agent.respond(q, fake_conv_id, org)
            total = time.perf_counter() - t0
            llm_path = time.perf_counter() - t_llm
            print(f"  Agent respond:   {llm_path:.2f}s")
            print(f"  TOTAL:           {total:.2f}s")
            print(f"  Reply length:    {len(out)} chars")
        except Exception as exc:
            print(f"  ERROR: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
