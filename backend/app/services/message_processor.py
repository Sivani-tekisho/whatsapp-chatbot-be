"""Incoming WhatsApp message processing pipeline."""

import logging
from uuid import UUID

from supabase import Client

from app.agents.company_agent import CompanyAgent
from app.core.config import Settings
from app.services.conversation_service import ConversationService
from app.services.whatsapp_service import WhatsAppService, normalize_whatsapp_recipient
from app.utils.whatsapp_text import format_for_whatsapp

logger = logging.getLogger(__name__)


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
        org_id = self._settings.default_organization_id
        query = self._db.table("organizations").select("*")
        if org_id:
            query = query.eq("id", org_id)
        result = query.limit(1).execute()
        return result.data[0] if result.data else {}

    async def process_message(
        self,
        phone: str,
        text: str,
        whatsapp_message_id: str | None = None,
    ) -> str:
        """Full pipeline: save user → RAG/LLM → send WhatsApp → save assistant."""
        phone = normalize_whatsapp_recipient(phone)
        conversation = self._conversations.get_or_create(phone)
        conversation_id = UUID(conversation["id"])
        org_settings = self._get_org_settings()

        # Persist inbound message before generating reply (audit + dashboard)
        self._conversations.save_message(conversation_id, "user", text)

        greeting = org_settings.get("greeting_message", "")
        is_greeting_trigger = text.strip().lower() in {"hi", "hello", "hey", "start"}

        if is_greeting_trigger and greeting:
            response = greeting
        else:
            response = await self._agent.respond(text, conversation_id, org_settings)

        response = format_for_whatsapp(response)

        if whatsapp_message_id:
            try:
                await self._whatsapp.mark_as_read(whatsapp_message_id)
            except Exception as exc:
                logger.warning("Failed to mark message read: %s", exc)

        # Send first — only save assistant message after Meta accepts delivery
        await self._whatsapp.send_text(phone, response)
        self._conversations.save_message(conversation_id, "assistant", response)
        logger.info("Saved conversation and sent reply for +%s", phone)
        return response
