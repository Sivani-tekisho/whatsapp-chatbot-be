"""Company RAG agent — orchestrates retrieval and LLM response."""

import asyncio
import logging
import time
from uuid import UUID

from app.core.logging_config import wa_log

logger = logging.getLogger(__name__)

from app import company_branding as branding
from app.core.config import Settings
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.prompt_service import PromptService
from app.services.rag_service import RAGService
from app.utils.whatsapp_text import format_for_whatsapp


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
    ) -> str:
        fallback = org_settings.get(
            "fallback_message", "I couldn't find that information."
        )
        company_name = branding.resolve_company_name(
            org_settings.get("name"),
            self._settings.company_name,
        )

        t0 = time.perf_counter()
        history, context_chunks = await asyncio.gather(
            asyncio.to_thread(self._memory.load_history, conversation_id),
            asyncio.to_thread(self._rag.retrieve_context, user_message),
        )
        wa_log(
            logger,
            "RAG DONE",
            f"{time.perf_counter() - t0:.1f}s chunks={len(context_chunks)}",
        )

        if not self._rag.has_relevant_context(context_chunks):
            messages = self._prompts.build_no_rag_prompt(
                company_name=company_name,
                fallback_message=fallback,
                user_message=user_message,
                history=history,
                org_settings=org_settings,
            )
            t1 = time.perf_counter()
            out = await self._llm.generate(messages)
            wa_log(
                logger,
                "LLM DONE",
                f"{self._llm.model} {time.perf_counter() - t1:.1f}s",
            )
            return format_for_whatsapp(out)

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

        t1 = time.perf_counter()
        out = await self._llm.generate(messages)
        wa_log(
            logger,
            "LLM DONE",
            f"{self._llm.model} {time.perf_counter() - t1:.1f}s",
        )
        return format_for_whatsapp(out)
