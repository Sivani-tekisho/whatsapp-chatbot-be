"""Company RAG agent — orchestrates retrieval and LLM response."""

import asyncio
import logging
import time
from uuid import UUID

from app import company_branding as branding
from app.core.config import Settings
from app.core.logging_config import wa_log
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.prompt_service import PromptService
from app.services.rag_service import RAGService
from app.utils.whatsapp_text import format_for_whatsapp

logger = logging.getLogger(__name__)

# ── Messages that don't need RAG/Pinecone at all ─────────────────────────────
_SKIP_RAG_TOKENS: frozenset[str] = frozenset({
    "hi", "hello", "hey", "heyy", "heyyy",
    "thanks", "thank", "thank you", "thankyou", "ty",
    "ok", "okay", "k", "cool", "got it", "noted",
    "bye", "goodbye", "see you", "take care",
    "start", "help", "menu",
    "yes", "no", "yep", "nope", "sure",
})


def _should_skip_rag(text: str) -> bool:
    """Return True when the message is a simple social phrase — no RAG needed."""
    normalized = text.strip().lower().rstrip("!?.,")
    return normalized in _SKIP_RAG_TOKENS or len(normalized) <= 3


class CompanyAgent:
    def __init__(
        self,
        settings: Settings,
        rag_service: RAGService,
        llm_service: LLMService,
        prompt_service: PromptService,
        memory_service: MemoryService,
    ) -> None:
        self._settings = settings
        self._rag = rag_service
        self._llm = llm_service
        self._prompts = prompt_service
        self._memory = memory_service

    async def respond(
        self,
        user_message: str,
        conversation_id: UUID,
        org_settings: dict,
        intent: str = "knowledge",
    ) -> str:
        t0 = time.perf_counter()

        fallback = org_settings.get(
            "fallback_message", "I couldn't find that information."
        )
        company_name = branding.resolve_company_name(
            org_settings.get("name"),
            self._settings.company_name,
        )

        # Skip RAG only for pure social tokens / very short messages.
        # FAQ and knowledge intents always query Pinecone so product/company
        # questions like "about tekisho" or "what is emailq" get real KB context.
        skip_rag = _should_skip_rag(user_message)

        if skip_rag:
            wa_log(logger, "RAG SKIP", f"intent={intent} (social/short) → no Pinecone query")
            history = await asyncio.to_thread(self._memory.load_history, conversation_id)
            context_chunks: list[str] = []
            t_rag = 0.0
        else:
            # Parallel: async embed+RAG + history load simultaneously
            t_rag_start = time.perf_counter()
            history, context_chunks = await asyncio.gather(
                asyncio.to_thread(self._memory.load_history, conversation_id),
                self._rag.retrieve_context_async(user_message),
            )
            t_rag = time.perf_counter() - t_rag_start
            wa_log(
                logger,
                "RAG DONE",
                f"{t_rag:.2f}s  chunks={len(context_chunks)}",
            )

        if skip_rag or not self._rag.has_relevant_context(context_chunks):
            messages = self._prompts.build_no_rag_prompt(
                company_name=company_name,
                fallback_message=fallback,
                user_message=user_message,
                history=history,
                org_settings=org_settings,
            )
        else:
            system_prompt = self._prompts.build_rag_system_prompt(
                company_name=company_name,
                custom_prompt=org_settings.get("system_prompt"),
                fallback_message=fallback,
                org_settings=org_settings,
            )
            messages = self._prompts.build_rag_prompt(
                system_prompt=system_prompt,
                context_chunks=context_chunks,
                user_message=user_message,
                history=history,
                company_name=company_name,
            )

        t_llm_start = time.perf_counter()
        out = await self._llm.generate_streaming(messages)
        t_llm = time.perf_counter() - t_llm_start
        t_total = time.perf_counter() - t0

        wa_log(
            logger,
            "LLM DONE",
            f"{self._llm.model}  llm={t_llm:.2f}s  rag={t_rag:.2f}s  agent_total={t_total:.2f}s",
        )
        return format_for_whatsapp(out)

    async def respond_streaming(
        self,
        user_message: str,
        conversation_id: UUID,
        org_settings: dict,
        intent: str = "knowledge",
        send_fn=None,  # async callable(text: str) -> None
    ) -> str:
        """Like respond() but sends each sentence to WhatsApp as soon as it streams.

        The user sees the first bubble in ~400ms instead of waiting for the full reply.
        Returns the complete reply text (for DB saving + response cache).
        """
        t0 = time.perf_counter()

        fallback = org_settings.get("fallback_message", "I couldn't find that information.")
        company_name = branding.resolve_company_name(
            org_settings.get("name"),
            self._settings.company_name,
        )

        skip_rag = _should_skip_rag(user_message)

        if skip_rag:
            wa_log(logger, "RAG SKIP", f"intent={intent} (social/short, streaming path)")
            history = await asyncio.to_thread(self._memory.load_history, conversation_id)
            context_chunks: list[str] = []
            t_rag = 0.0
        else:
            t_rag_start = time.perf_counter()
            history, context_chunks = await asyncio.gather(
                asyncio.to_thread(self._memory.load_history, conversation_id),
                self._rag.retrieve_context_async(user_message),
            )
            t_rag = time.perf_counter() - t_rag_start
            wa_log(logger, "RAG DONE", f"{t_rag:.2f}s  chunks={len(context_chunks)}")

        if skip_rag or not self._rag.has_relevant_context(context_chunks):
            messages = self._prompts.build_no_rag_prompt(
                company_name=company_name,
                fallback_message=fallback,
                user_message=user_message,
                history=history,
                org_settings=org_settings,
            )
        else:
            system_prompt = self._prompts.build_rag_system_prompt(
                company_name=company_name,
                custom_prompt=org_settings.get("system_prompt"),
                fallback_message=fallback,
                org_settings=org_settings,
            )
            messages = self._prompts.build_rag_prompt(
                system_prompt=system_prompt,
                context_chunks=context_chunks,
                user_message=user_message,
                history=history,
                company_name=company_name,
            )

        t_llm_start = time.perf_counter()

        if send_fn is not None:
            # Progressive: send each sentence as it streams
            full_text = await self._llm.stream_to_sender(messages, send_fn)
        else:
            # Fallback: collect full reply
            full_text = await self._llm.generate_streaming(messages)

        t_llm = time.perf_counter() - t_llm_start
        t_total = time.perf_counter() - t0
        wa_log(
            logger,
            "LLM PROGRESSIVE DONE",
            f"{self._llm.model}  llm={t_llm:.2f}s  rag={t_rag:.2f}s  total={t_total:.2f}s",
        )
        return format_for_whatsapp(full_text)
