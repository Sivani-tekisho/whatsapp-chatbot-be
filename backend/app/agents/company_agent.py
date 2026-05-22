"""Company RAG agent — orchestrates retrieval and LLM response."""

import asyncio
import logging
import time
from uuid import UUID

from app import company_branding as branding
from app.core.config import Settings
from app.core.logging_config import wa_log
from app.rag.query_router import route_query
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.prompt_service import PromptService
from app.services.rag_service import RAGService
from app.services.response_cache import ResponseCacheService
from app.utils.query_normalize import cache_key_for_message
from app.utils.whatsapp_text import format_for_whatsapp

logger = logging.getLogger(__name__)


def _should_cache_response(response: str, fallback: str) -> bool:
    """Avoid caching useless fallback-only replies (so retries can succeed)."""
    r = (response or "").strip().lower()
    f = (fallback or "").strip().lower()
    if len(r) < 20:
        return False
    if f and r == f:
        return False
    refusal_phrases = (
        "couldn't find",
        "could not find",
        "not find that information",
        "no information available",
    )
    if any(p in r for p in refusal_phrases) and len(r) < 150:
        return False
    return True


class CompanyAgent:
    def __init__(
        self,
        settings: Settings,
        rag_service: RAGService,
        llm_service: LLMService,
        prompt_service: PromptService,
        memory_service: MemoryService,
        response_cache: ResponseCacheService,
    ) -> None:
        self._settings = settings
        self._rag = rag_service
        self._llm = llm_service
        self._prompts = prompt_service
        self._memory = memory_service
        self._cache = response_cache

    async def respond(
        self,
        user_message: str,
        conversation_id: UUID,
        org_settings: dict,
    ) -> str:
        fallback = org_settings.get(
            "fallback_message", "I couldn't find that information."
        )
        company_name = branding.resolve_company_name(
            org_settings.get("name"),
            self._settings.company_name,
        )
        org_id = str(
            org_settings.get("id") or self._settings.default_organization_id or "default"
        )

        query_route = route_query(
            user_message, self._settings.pinecone_namespaces
        )
        intent = query_route.intent

        cache_key = cache_key_for_message(user_message, org_id, company_name)
        cached = await asyncio.to_thread(self._cache.get, cache_key)
        if cached:
            wa_log(logger, "AGENT", f"cache hit intent={intent or 'general'}")
            return cached

        t0 = time.perf_counter()
        skip_history = query_route.skip_chat_history

        if skip_history:
            history: list[dict] = []
            context_chunks = await asyncio.to_thread(
                self._rag.retrieve_context, user_message
            )
        else:
            history, context_chunks = await asyncio.gather(
                asyncio.to_thread(self._memory.load_history, conversation_id),
                asyncio.to_thread(self._rag.retrieve_context, user_message),
            )

        has_rag = self._rag.has_relevant_context(context_chunks)
        wa_log(
            logger,
            "RAG DONE",
            f"{time.perf_counter() - t0:.1f}s intent={intent or 'general'} "
            f"chunks={len(context_chunks)} has_rag={has_rag} history={len(history)}",
        )

        if not has_rag:
            messages = self._prompts.build_no_rag_prompt(
                company_name=company_name,
                fallback_message=fallback,
                user_message=user_message,
                history=history,
                org_settings=org_settings,
                intent=intent,
            )
        else:
            system_prompt = self._prompts.build_rag_system_prompt(
                company_name=company_name,
                custom_prompt=org_settings.get("system_prompt"),
                fallback_message=fallback,
                org_settings=org_settings,
                detected_intent=intent,
            )
            messages = self._prompts.build_rag_prompt(
                system_prompt=system_prompt,
                context_chunks=context_chunks,
                user_message=user_message,
                history=history,
                company_name=company_name,
                intent=intent,
                org_settings=org_settings,
            )

        t1 = time.perf_counter()
        out = await self._llm.generate(messages)
        wa_log(
            logger,
            "LLM DONE",
            f"{self._llm.model} {time.perf_counter() - t1:.1f}s intent={intent or 'general'}",
        )
        response = format_for_whatsapp(out)

        if _should_cache_response(response, fallback):
            await asyncio.to_thread(self._cache.set, cache_key, response)
        else:
            wa_log(logger, "CACHE SKIP", "fallback-only reply not stored")

        wa_log(logger, "AGENT TOTAL", f"{time.perf_counter() - t0:.1f}s")
        return response
