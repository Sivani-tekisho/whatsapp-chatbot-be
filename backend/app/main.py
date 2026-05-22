"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import conversations, documents, settings as settings_api, webhook
from app.core.config import get_settings
from app.core.logging_config import setup_logging, wa_log

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    settings = get_settings()
    wa_log(logger, "SERVER START", settings.app_name)
    wa_log(
        logger,
        "META CALLBACK URL",
        "https://YOUR-NGROK-HOST/webhook OR /api/v1/webhook (both work)",
    )
    wa_log(logger, "WAITING", "Real chats appear as: [WHATSAPP] INBOUND POST -> USER MESSAGE -> REPLY SENT")
    wa_log(logger, "OPENAI MODEL", settings.openai_model or "gpt-4o-mini")

    async def _warmup() -> None:
        try:
            from app.dependencies import get_rag_service

            s = get_settings()
            if s.rag_provider.lower() == "pinecone" and not s.pinecone_host.strip():
                wa_log(
                    logger,
                    "WARMUP HINT",
                    "Add PINECONE_HOST to .env to skip slow describe_index on each deploy",
                )
            await asyncio.to_thread(get_rag_service().retrieve_context, "warmup")
            wa_log(logger, "WARMUP OK", "Pinecone + embeddings ready (singleton cached)")
        except Exception as exc:
            wa_log(logger, "WARMUP SKIP", str(exc)[:120])

    await _warmup()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Meta webhook: support both paths (teammate stacks often use /api/v1/webhook)
    app.include_router(webhook.router)
    app.include_router(webhook.router, prefix=settings.api_prefix)
    app.include_router(conversations.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.include_router(settings_api.router, prefix=settings.api_prefix)

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/health/whatsapp")
    async def health_whatsapp():
        """Verify Meta token can access the configured phone number ID."""
        import httpx

        from app.services.whatsapp_service import format_graph_api_error

        s = get_settings()
        if not s.whatsapp_access_token or not s.whatsapp_phone_number_id:
            return {
                "ok": False,
                "error": "Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in backend/.env",
            }

        async with httpx.AsyncClient(timeout=15.0) as client:
            me = await client.get(
                "https://graph.facebook.com/v21.0/me",
                params={"access_token": s.whatsapp_access_token},
            )
            phone = await client.get(
                f"https://graph.facebook.com/v21.0/{s.whatsapp_phone_number_id}",
                params={"access_token": s.whatsapp_access_token},
            )

        me_body = me.json() if me.headers.get("content-type", "").startswith("application/json") else {}
        token_looks_like_user = "name" in me_body and me.status_code == 200

        if phone.is_success:
            data = phone.json()
            return {
                "ok": True,
                "phone_number_id": s.whatsapp_phone_number_id,
                "display_phone_number": data.get("display_phone_number"),
                "verified_name": data.get("verified_name"),
                "message": "Credentials OK — outbound WhatsApp should work.",
            }

        result = {
            "ok": False,
            "phone_number_id": s.whatsapp_phone_number_id,
            "error": format_graph_api_error(phone),
        }
        if token_looks_like_user:
            result["fix"] = (
                "Token is a Facebook user token. Use the token from "
                "Meta → WhatsApp → API Setup → Generate access token."
            )
        return result

    @app.get("/webhook/status")
    async def webhook_status():
        """Dashboard: Meta connection state (does not poll Meta — reads local memory)."""
        from app.services.webhook_activity import get_summary

        s = get_settings()
        summary = get_summary()
        return {
            "webhook_path": "/webhook",
            "verify_token_set": bool(s.verify_token),
            "whatsapp_phone_id": s.whatsapp_phone_number_id or None,
            **summary,
            "status_label": (
                "Receiving WhatsApp messages"
                if summary["whatsapp_connected"]
                else (
                    "Meta verified URL only — no user messages yet"
                    if summary["meta_verified"]
                    else "Not verified — set callback URL in Meta"
                )
            ),
        }

    return app


app = create_app()
