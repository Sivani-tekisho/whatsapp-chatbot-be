"""
End-to-end flow checks: routing, prompts (website in signup), optional live LLM.

Run from backend/:  python scripts/test_flow.py
Skip LLM:          python scripts/test_flow.py --no-llm
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
import uuid

# Clear prompt cache so file edits apply
from app.services import prompt_service as ps

ps._load_whatsapp_system_template.cache_clear()
ps._load_intent_policy_template.cache_clear()


CASES = [
    ("How do I signup?", "signup", "tekisho.ai"),
    ("Can you tell me pricing for leadq", "leadq", None),
    ("Do you have free trial", "trial", "tekisho"),
    ("What are your business hours", "hours", None),
    ("Tekisho services", "services", "tekisho"),
    ("What is the weather today", "general", None),
]


def test_routing() -> list[str]:
    from app.rag.query_router import route_query

    errors = []
    ns = "__default__,vocalq,leadq,emailq"
    for query, expected_intent, _ in CASES:
        route = route_query(query, ns)
        got = route.intent or "general"
        exp = expected_intent or "general"
        if expected_intent and got != expected_intent:
            errors.append(f"routing: {query!r} expected {exp} got {got}")
    return errors


def test_prompts() -> list[str]:
    from app.core.config import get_settings
    from app.services.prompt_service import render_whatsapp_system_prompt

    errors = []
    s = get_settings()
    for query, intent, must_contain in CASES:
        prompt = render_whatsapp_system_prompt(
            company_name="Tekisho Infotech",
            fallback_message="I couldn't find that information.",
            detected_intent=intent if intent != "general" else None,
        )
        if "Tekisho Infotech" not in prompt and "{{" in prompt:
            errors.append(f"prompt: unreplaced placeholder in {query!r}")
        if must_contain and must_contain.lower() not in prompt.lower():
            errors.append(f"prompt: {query!r} missing {must_contain!r} in system prompt")
        if intent == "signup" and "tekisho.ai" not in prompt.lower():
            errors.append(f"prompt: signup missing website URL")
    return errors


async def test_agent(no_llm: bool) -> list[str]:
    from app.core.config import get_settings
    from app.dependencies import get_company_agent

    if no_llm:
        return []

    errors = []
    agent = get_company_agent()
    org = {
        "id": get_settings().default_organization_id,
        "name": "Tekisho Infotech",
        "fallback_message": "I couldn't find that information.",
    }
    conv_id = uuid.uuid4()

    for query, intent, must in [("How do I signup?", "signup", "tekisho")]:
        t0 = time.perf_counter()
        try:
            reply = await agent.respond(query, conv_id, org)
            elapsed = time.perf_counter() - t0
            low = reply.lower()
            print(f"\nLLM [{elapsed:.1f}s] Q: {query}")
            print(f"  A: {reply[:280]}{'...' if len(reply) > 280 else ''}")
            if must and must not in low:
                errors.append(f"llm: reply missing {must!r}")
            if "couldn't find" in low and len(reply) < 120:
                errors.append(f"llm: fallback-only reply for {query!r}")
        except Exception as exc:
            errors.append(f"llm: {query!r} failed: {exc}")
    return errors


async def test_latency_sample() -> None:
    from app.dependencies import get_rag_service

    rag = get_rag_service()
    for q in ["How do I signup?", "Tekisho services"]:
        t0 = time.perf_counter()
        chunks = await asyncio.to_thread(rag.retrieve_context, q)
        print(f"RAG {q!r}: {time.perf_counter() - t0:.2f}s chunks={len(chunks)}")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true", help="Skip OpenAI calls")
    args = parser.parse_args()

    print("=== Flow test: WhatsApp chatbot ===\n")

    all_errors: list[str] = []
    print("1. Query routing")
    all_errors.extend(test_routing())
    print("   OK" if not all_errors else f"   FAIL: {all_errors}")

    print("2. Prompts (website/contact injected)")
    pe = test_prompts()
    all_errors.extend(pe)
    print("   OK" if not pe else f"   FAIL: {pe}")

    print("3. RAG latency sample")
    await test_latency_sample()

    print("4. Live LLM reply (signup)")
    le = await test_agent(args.no_llm)
    all_errors.extend(le)
    if args.no_llm:
        print("   skipped (--no-llm)")
    elif not le:
        print("   OK")

    print("\n" + ("ALL PASSED" if not all_errors else f"FAILED ({len(all_errors)} issues)"))
    for e in all_errors:
        print(f"  - {e}")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
