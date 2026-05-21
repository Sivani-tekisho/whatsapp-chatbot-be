"""Incoming WhatsApp message processing pipeline."""



import asyncio

import logging

import time

from uuid import UUID



from supabase import Client



from app.agents.company_agent import CompanyAgent

from app.cache import cache_get, cache_set, org_cache

from app.core.config import Settings

from app.core.logging_config import wa_log

from app.services.conversation_service import ConversationService

from app.services.intent_classifier import classify_intent, get_social_reply

from app.services.memory_service import MemoryService

from app.services.response_cache import get_cached_response, set_cached_response

from app.services.whatsapp_service import WhatsAppService, normalize_whatsapp_recipient

from app.utils.whatsapp_text import format_for_whatsapp



logger = logging.getLogger(__name__)

_ORG_CACHE_KEY = "org_settings"




class MessageProcessor:

    def __init__(

        self,

        db: Client,

        settings: Settings,

        agent: CompanyAgent,

        conversation_service: ConversationService,

        whatsapp_service: WhatsAppService,

        memory_service: MemoryService | None = None,

    ) -> None:

        self._db = db

        self._settings = settings

        self._agent = agent

        self._conversations = conversation_service

        self._whatsapp = whatsapp_service

        self._memory = memory_service



    def _get_org_settings(self) -> dict:
        hit, cached = cache_get(org_cache, _ORG_CACHE_KEY)
        if hit:
            wa_log(logger, "CACHE HIT", "org_settings served from TTLCache")
            return cached  # type: ignore[return-value]

        wa_log(logger, "CACHE MISS", "org_settings → fetching from Supabase")
        t_db = time.perf_counter()

        org_id = self._settings.default_organization_id

        query = self._db.table("organizations").select(
            "id,name,bot_name,greeting_message,fallback_message,system_prompt"
        )

        if org_id:

            query = query.eq("id", org_id)

        result = query.limit(1).execute()

        row = result.data[0] if result.data else {}

        wa_log(logger, "DB FETCH", f"org_settings in {time.perf_counter() - t_db:.3f}s")

        cache_set(org_cache, _ORG_CACHE_KEY, row)

        return row



    async def process_message(

        self,

        phone: str,

        text: str,

        whatsapp_message_id: str | None = None,

    ) -> str:

        """Full message pipeline: classify → shortcut/cache → RAG/LLM → send → save."""

        t0 = time.perf_counter()

        phone = normalize_whatsapp_recipient(phone)

        # Fire mark-as-read immediately so user sees blue ticks before LLM responds
        if whatsapp_message_id:
            asyncio.create_task(self._mark_read_safe(whatsapp_message_id))

        # ── Step 1: Intent classification (pure Python, zero I/O) ────────────
        intent = classify_intent(text)
        wa_log(logger, "INTENT", f"{intent}  msg={text[:60]}")

        # ── Instant ACK for non-social queries ────────────────────────────────
        # React to the user's message immediately so they know we received it.
        if intent != "social" and len(text.strip()) > 3 and whatsapp_message_id:
            asyncio.create_task(
                self._whatsapp.send_reaction(phone, whatsapp_message_id, "\U0001f914")  # 🤔
            )

        # ── Step 2: Social short-circuit (no DB, no RAG, no LLM) ─────────────
        if intent == "social":
            reply = get_social_reply(text)
            _, (conversation, _) = await asyncio.gather(
                self._whatsapp.send_text(phone, reply),
                asyncio.to_thread(self._conversations.get_or_create, phone),
            )
            conversation_id = UUID(conversation["id"])
            asyncio.create_task(self._save_messages_async(conversation_id, text, reply))
            if self._memory is not None:
                self._memory.append_to_cache(conversation_id, "user", text)
                self._memory.append_to_cache(conversation_id, "assistant", reply)
            wa_log(logger, "TOTAL RESPONSE TIME",
                   f"+{phone}  SOCIAL  TOTAL={time.perf_counter()-t0:.2f}s")
            return reply

        # ── Step 3: Parallel DB fetch (needed for all non-social paths) ───────
        t_db_start = time.perf_counter()

        (conversation, is_new_conversation), org_settings = await asyncio.gather(

            asyncio.to_thread(self._conversations.get_or_create, phone),

            asyncio.to_thread(self._get_org_settings),

        )

        conversation_id = UUID(conversation["id"])

        t_db = time.perf_counter() - t_db_start

        wa_log(logger, "DB FETCH", f"conversation+org in {t_db:.3f}s  phone=+{phone}  new={is_new_conversation}")

        # ── Step 4: Canned greeting (very first message) ──────────────────────
        greeting = org_settings.get("greeting_message", "")
        normalized = text.strip().lower().strip("!?.,")
        is_greeting_only = normalized in {"hi", "hello", "hey", "start"}
        use_canned_greeting = (is_greeting_only and greeting and is_new_conversation)

        if use_canned_greeting:
            response = format_for_whatsapp(greeting)
            wa_log(logger, "GREETING", f"+{phone} first message → canned greeting")
            await self._whatsapp.send_text(phone, response)
            asyncio.create_task(self._save_messages_async(conversation_id, text, response))
            if self._memory is not None:
                self._memory.append_to_cache(conversation_id, "user", text)
                self._memory.append_to_cache(conversation_id, "assistant", response)
            wa_log(logger, "TOTAL RESPONSE TIME",
                   f"+{phone}  GREETING  TOTAL={time.perf_counter()-t0:.2f}s")
            return response

        # ── Step 5: Response cache (FAQ & knowledge) ──────────────────────────
        # Load existing conversation history now — it's RAM-cached so nearly free.
        # If the user has prior turns we MUST skip the response cache: same question
        # can deserve a different answer depending on what was already discussed
        # (e.g. "tell me about tekisho" on the 5th message ≠ first message).
        existing_history: list[dict] = []
        if self._memory is not None:
            existing_history = await asyncio.to_thread(
                self._memory.load_history, conversation_id
            )

        has_history = bool(existing_history)
        cached = None
        if not has_history:
            cached = await get_cached_response(text)

        if cached:
            wa_log(logger, "RESPONSE CACHE HIT", f"+{phone}")
            await self._whatsapp.send_text(phone, cached)
            asyncio.create_task(self._save_messages_async(conversation_id, text, cached))
            if self._memory is not None:
                self._memory.append_to_cache(conversation_id, "user", text)
                self._memory.append_to_cache(conversation_id, "assistant", cached)
            wa_log(logger, "TOTAL RESPONSE TIME",
                   f"+{phone}  RCACHE  TOTAL={time.perf_counter()-t0:.2f}s")
            return cached

        if has_history:
            wa_log(logger, "CACHE BYPASS", f"+{phone}  {len(existing_history)} prior turns → LLM with context")

        # Step 6: Full RAG + LLM pipeline
        # stream_to_sender streams from OpenAI then delivers ONE WhatsApp message.
        t_agent_start = time.perf_counter()

        async def _send(text: str) -> None:
            try:
                await self._whatsapp.send_text(phone, text)
            except Exception as exc:
                logger.warning("send_text failed: %s", exc)

        response = await self._agent.respond_streaming(
            text, conversation_id, org_settings, intent=intent, send_fn=_send
        )
        t_agent = time.perf_counter() - t_agent_start

        # DB save is fire-and-forget (streaming already sent to WhatsApp above)
        asyncio.create_task(self._save_messages_async(conversation_id, text, response))

        if self._memory is not None:

            self._memory.append_to_cache(conversation_id, "user", text)

            self._memory.append_to_cache(conversation_id, "assistant", response)

        # Cache the reply for future identical questions
        asyncio.create_task(set_cached_response(text, response))

        t_total = time.perf_counter() - t0

        wa_log(
            logger,
            "TOTAL RESPONSE TIME",
            f"+{phone}  db={t_db:.2f}s  agent={t_agent:.2f}s  TOTAL={t_total:.2f}s",
        )

        return response

    async def _save_messages_async(
        self, conversation_id: UUID, user_text: str, assistant_text: str
    ) -> None:
        """Save both turns to Supabase — silently swallows errors so a DB hiccup
        never crashes the pipeline or surfaces to the user."""
        try:
            await asyncio.gather(
                asyncio.to_thread(
                    self._conversations.save_message, conversation_id, "user", user_text
                ),
                asyncio.to_thread(
                    self._conversations.save_message, conversation_id, "assistant", assistant_text
                ),
            )
        except Exception as exc:
            logger.warning("_save_messages_async failed: %s", exc)

    async def _mark_read_safe(self, message_id: str) -> None:

        try:

            await self._whatsapp.mark_as_read(message_id)

        except Exception as exc:

            logger.warning("Failed to mark message read: %s", exc)


