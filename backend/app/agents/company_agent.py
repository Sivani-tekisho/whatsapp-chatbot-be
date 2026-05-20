"""Company RAG agent — orchestrates retrieval and LLM response."""

from uuid import UUID

from app.core.config import Settings
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.prompt_service import PromptService
from app.services.rag_service import RAGService


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
        history = self._memory.load_history(conversation_id)
        context_chunks = self._rag.retrieve_context(user_message)

        fallback = org_settings.get(
            "fallback_message", "I couldn't find that information."
        )
        company_name = org_settings.get("name", self._settings.company_name)

        if not self._rag.has_relevant_context(context_chunks):
            messages = self._prompts.build_no_rag_prompt(
                company_name=company_name,
                fallback_message=fallback,
                user_message=user_message,
                history=history,
            )
            return await self._llm.generate(messages)

        system_prompt = self._prompts.build_system_prompt(
            company_name=company_name,
            custom_prompt=org_settings.get("system_prompt"),
            fallback_message=fallback,
        )

        messages = self._prompts.build_rag_prompt(
            system_prompt=system_prompt,
            context_chunks=context_chunks,
            user_message=user_message,
            history=history,
        )

        return await self._llm.generate(messages)
