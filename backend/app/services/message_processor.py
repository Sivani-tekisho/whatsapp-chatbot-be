"""Incoming WhatsApp message processing pipeline."""



import asyncio

import logging

import time

from uuid import UUID



from supabase import Client



from app.agents.company_agent import CompanyAgent

from app.core.config import Settings

from app.core.logging_config import wa_log

from app.services.conversation_service import ConversationService

from app.services.whatsapp_service import WhatsAppService, normalize_whatsapp_recipient

from app.utils.whatsapp_text import format_for_whatsapp



logger = logging.getLogger(__name__)



_ORG_CACHE: dict | None = None

_ORG_CACHE_AT = 0.0

_ORG_CACHE_TTL_SEC = 90.0





class MessageProcessor:

    def __init__(

        self,

        db: Client,

        settings: Settings,

        agent: CompanyAgent,

        conversation_service: ConversationService,

        whatsapp_service: WhatsAppService,

    ) -> None:

        self._db = db

        self._settings = settings

        self._agent = agent

        self._conversations = conversation_service

        self._whatsapp = whatsapp_service



    def _get_org_settings(self) -> dict:

        global _ORG_CACHE, _ORG_CACHE_AT

        now = time.time()

        if _ORG_CACHE is not None and now - _ORG_CACHE_AT < _ORG_CACHE_TTL_SEC:

            return _ORG_CACHE



        org_id = self._settings.default_organization_id

        # Match 002_chat_only_pinecone.sql — contact info uses .env / company_branding.py
        query = self._db.table("organizations").select(
            "id,name,bot_name,greeting_message,fallback_message,system_prompt"
        )

        if org_id:

            query = query.eq("id", org_id)

        result = query.limit(1).execute()

        row = result.data[0] if result.data else {}

        _ORG_CACHE = row

        _ORG_CACHE_AT = now

        return row



    async def process_message(

        self,

        phone: str,

        text: str,

        whatsapp_message_id: str | None = None,

    ) -> str:

        """Save user → RAG/LLM → send WhatsApp → save assistant."""

        t0 = time.perf_counter()

        phone = normalize_whatsapp_recipient(phone)



        conversation, org_settings = await asyncio.gather(

            asyncio.to_thread(self._conversations.get_or_create, phone),

            asyncio.to_thread(self._get_org_settings),

        )

        conversation_id = UUID(conversation["id"])

        t_db = time.perf_counter() - t0



        greeting = org_settings.get("greeting_message", "")
        normalized = text.strip().lower().strip("!?.,")
        is_greeting_only = normalized in {"hi", "hello", "hey", "start"}
        prior_messages = await asyncio.to_thread(
            self._conversations.count_messages, conversation_id
        )
        # Canned greeting only on the very first message in this chat thread
        use_canned_greeting = (
            is_greeting_only and greeting and prior_messages == 0
        )

        if use_canned_greeting:
            response = format_for_whatsapp(greeting)
            t_agent = 0.0
            wa_log(logger, "GREETING", f"+{phone} first message → canned greeting")
        else:

            t_agent_start = time.perf_counter()

            # Agent runs before persisting user message (avoids duplicate in LLM history)

            response = await self._agent.respond(text, conversation_id, org_settings)

            t_agent = time.perf_counter() - t_agent_start



        wa_log(

            logger,

            "REPLY READY",

            f"+{phone} db={t_db:.1f}s agent={t_agent:.1f}s total={time.perf_counter() - t0:.1f}s",

        )



        t_send_start = time.perf_counter()

        await self._whatsapp.send_text(phone, response)

        t_send = time.perf_counter() - t_send_start



        await asyncio.gather(

            asyncio.to_thread(

                self._conversations.save_message, conversation_id, "user", text

            ),

            asyncio.to_thread(

                self._conversations.save_message, conversation_id, "assistant", response

            ),

        )



        if whatsapp_message_id:

            asyncio.create_task(self._mark_read_safe(whatsapp_message_id))



        wa_log(

            logger,

            "REPLY SENT",

            f"+{phone} wa={t_send:.1f}s total {time.perf_counter() - t0:.1f}s",

        )

        return response



    async def _mark_read_safe(self, message_id: str) -> None:

        try:

            await self._whatsapp.mark_as_read(message_id)

        except Exception as exc:

            logger.warning("Failed to mark message read: %s", exc)


