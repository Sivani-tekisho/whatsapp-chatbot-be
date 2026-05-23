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
    settings = get_settings()
    wa_log(logger, "SERVER START", settings.app_name)
    wa_log(
        logger,
        "META CALLBACK URL",
        "https://YOUR-NGROK-HOST/webhook OR /api/v1/webhook (both work)",
    )
    wa_log(logger, "WAITING", "Real chats appear as: [WHATSAPP] INBOUND POST → USER MESSAGE → REPLY SENT")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
    )

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Webhook at /webhook (Meta callback URL should be https://your-host/webhook)
    app.include_router(webhook.router)
    app.include_router(conversations.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.include_router(settings_api.router, prefix=settings.api_prefix)

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

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
