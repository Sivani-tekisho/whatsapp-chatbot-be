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

_GREETING_WORDS = frozenset({"hi", "hello", "hey", "start"})


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
        """Generate reply -> send WhatsApp -> save DB in background."""
        t0 = time.perf_counter()
        phone = normalize_whatsapp_recipient(phone)

        conversation, org_settings = await asyncio.gather(
            asyncio.to_thread(self._conversations.get_or_create, phone),
            asyncio.to_thread(self._get_org_settings),
        )
        conversation_id = UUID(conversation["id"])
        t_setup = time.perf_counter() - t0

        normalized = text.strip().lower().strip("!?.,")
        is_greeting_only = normalized in _GREETING_WORDS
        greeting = org_settings.get("greeting_message", "")

        use_canned_greeting = False
        if is_greeting_only and greeting:
            has_prior = await asyncio.to_thread(
                self._conversations.has_messages, conversation_id
            )
            use_canned_greeting = not has_prior

        if use_canned_greeting:
            response = format_for_whatsapp(greeting)
            t_agent = 0.0
            wa_log(logger, "GREETING", f"+{phone} first message only")
        else:
            t_agent_start = time.perf_counter()
            response = await self._agent.respond(text, conversation_id, org_settings)
            t_agent = time.perf_counter() - t_agent_start

        t_pre_send = time.perf_counter() - t0
        wa_log(
            logger,
            "REPLY READY",
            f"+{phone} setup={t_setup:.1f}s agent={t_agent:.1f}s pre_send={t_pre_send:.1f}s",
        )

        t_send_start = time.perf_counter()
        await self._whatsapp.send_text(phone, response)
        t_send = time.perf_counter() - t_send_start

        asyncio.create_task(
            self._persist_messages(conversation_id, text, response)
        )
        if whatsapp_message_id:
            asyncio.create_task(self._mark_read_safe(whatsapp_message_id))

        wa_log(
            logger,
            "REPLY SENT",
            f"+{phone} meta_send={t_send:.1f}s E2E={time.perf_counter() - t0:.1f}s",
        )
        return response

    async def _persist_messages(
        self, conversation_id: UUID, user_text: str, assistant_text: str
    ) -> None:
        try:
            await asyncio.gather(
                asyncio.to_thread(
                    self._conversations.save_message,
                    conversation_id,
                    "user",
                    user_text,
                ),
                asyncio.to_thread(
                    self._conversations.save_message,
                    conversation_id,
                    "assistant",
                    assistant_text,
                ),
            )
        except Exception as exc:
            logger.exception("Failed to save messages: %s", exc)

    async def _mark_read_safe(self, message_id: str) -> None:
        try:
            await self._whatsapp.mark_as_read(message_id)
        except Exception as exc:
            logger.warning("Failed to mark message read: %s", exc)
