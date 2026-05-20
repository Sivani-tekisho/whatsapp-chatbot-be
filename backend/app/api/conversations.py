"""Conversation management API."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging_config import wa_log
from app.dependencies import get_conversation_service, get_whatsapp_service
from app.utils.whatsapp_text import format_for_whatsapp
import logging

logger = logging.getLogger(__name__)
from app.models.conversation import (
    Conversation,
    ConversationDetail,
    ConversationListResponse,
    DashboardMetrics,
    MessageResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics():
    service = get_conversation_service()
    return service.get_dashboard_metrics()


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    search: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    lite: bool = Query(False, description="Skip per-chat Supabase lookups (faster polling)"),
):
    service = get_conversation_service()
    items, total = service.list_conversations(
        search, status, limit, offset, include_previews=not lite
    )
    return ConversationListResponse(
        items=[Conversation(**c) for c in items],
        total=total,
    )


class SendReplyBody(BaseModel):
    message: str


class OutboundToNewBody(BaseModel):
    """Start or continue a thread by messaging a phone number from the admin UI."""

    phone: str
    message: str


class WelcomeTemplateBody(BaseModel):
    """Send Meta-approved welcome template to a new user."""

    phone: str
    template_name: str | None = None
    language_code: str | None = None
    body_parameters: list[str] | None = None


@router.get("/messaging-config")
async def get_messaging_config():
    """Template name/language for the dashboard (from .env)."""
    s = get_settings()
    params = [
        p.strip()
        for p in s.whatsapp_welcome_template_body_params.split(",")
        if p.strip()
    ]
    return {
        "welcome_template_name": s.whatsapp_welcome_template_name,
        "welcome_template_language": s.whatsapp_welcome_template_language,
        "welcome_template_body_params": params,
    }


@router.post("/welcome-template")
async def send_welcome_template(body: WelcomeTemplateBody):
    """
    Send the approved welcome template to a new phone number.
    Use this for users who have not messaged your business yet.
    """
    from app.services.whatsapp_service import normalize_whatsapp_recipient

    settings = get_settings()
    template_name = (body.template_name or settings.whatsapp_welcome_template_name).strip()
    language_code = (body.language_code or settings.whatsapp_welcome_template_language).strip()
    if not template_name:
        raise HTTPException(status_code=400, detail="Template name is not configured")

    body_params = body.body_parameters
    if not body_params and settings.whatsapp_welcome_template_body_params.strip():
        body_params = [
            p.strip()
            for p in settings.whatsapp_welcome_template_body_params.split(",")
            if p.strip()
        ]
    if not body_params:
        from app import company_branding as branding

        if branding.COMPANY_NAME:
            body_params = [branding.COMPANY_NAME]

    try:
        phone = normalize_whatsapp_recipient(body.phone.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = get_conversation_service()
    conv = service.get_or_create(phone)
    conversation_id = UUID(conv["id"])
    whatsapp = get_whatsapp_service()
    wa_message_id = None
    display_text = f"[WhatsApp template: {template_name}]"

    try:
        wa_log(
            logger,
            "ADMIN TEMPLATE",
            f"to +{phone} template={template_name} lang={language_code}",
        )
        graph_response = await whatsapp.send_template(
            phone,
            template_name,
            language_code,
            body_params,
        )
        wa_message_id = whatsapp.extract_sent_message_id(graph_response)
        if wa_message_id:
            wa_log(logger, "META ACCEPTED", f"wamid={wa_message_id} → +{phone}")
    except ValueError as exc:
        wa_log(logger, "ADMIN TEMPLATE FAILED", str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        wa_log(logger, "ADMIN TEMPLATE FAILED", str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    service.save_message(conversation_id, "assistant", display_text)
    return {
        "status": "sent",
        "phone": phone,
        "conversation_id": str(conversation_id),
        "whatsapp_message_id": wa_message_id,
        "template_name": template_name,
        "language_code": language_code,
    }


@router.post("/outbound")
async def send_outbound_to_phone(body: OutboundToNewBody):
    """
    Send the first (or next) WhatsApp message to a number typed in the dashboard.
    Creates the conversation row if it does not exist. Subject to Meta rules (e.g. 24h window, test allowlist).
    """
    from app.services.whatsapp_service import normalize_whatsapp_recipient

    text = format_for_whatsapp(body.message.strip())
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        phone = normalize_whatsapp_recipient(body.phone.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = get_conversation_service()
    conv = service.get_or_create(phone)
    conversation_id = UUID(conv["id"])
    whatsapp = get_whatsapp_service()
    wa_message_id = None

    try:
        wa_log(logger, "ADMIN OUTBOUND NEW", f"to +{phone}: {text[:80]}")
        graph_response = await whatsapp.send_text(phone, text)
        wa_message_id = whatsapp.extract_sent_message_id(graph_response)
        if wa_message_id:
            wa_log(logger, "META ACCEPTED", f"wamid={wa_message_id} → +{phone}")
    except ValueError as exc:
        wa_log(logger, "ADMIN OUTBOUND FAILED", str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        wa_log(logger, "ADMIN OUTBOUND FAILED", str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    service.save_message(conversation_id, "assistant", text)
    return {
        "status": "sent",
        "phone": phone,
        "conversation_id": str(conversation_id),
        "whatsapp_message_id": wa_message_id,
        "delivery_note": (
            "Meta accepted this message. If the user did not receive it, add their number "
            "in Meta → WhatsApp → API Setup → test numbers (dev mode), or ask them to "
            "message your business WhatsApp number first."
        ),
    }


class StatusUpdate(BaseModel):
    status: str


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: UUID):
    service = get_conversation_service()
    data = service.get_conversation_with_messages(conversation_id)
    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = [MessageResponse(**m) for m in data.pop("messages", [])]
    return ConversationDetail(**data, messages=messages)


@router.patch("/{conversation_id}/status")
async def update_conversation_status(conversation_id: UUID, body: StatusUpdate):
    if body.status not in ("active", "resolved"):
        raise HTTPException(status_code=400, detail="Invalid status")
    service = get_conversation_service()
    return service.update_status(conversation_id, body.status)


@router.post("/{conversation_id}/reply")
async def send_reply(conversation_id: UUID, body: SendReplyBody):
    """Send a WhatsApp text reply from admin (outbound via Meta API)."""
    text = format_for_whatsapp(body.message.strip())
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    service = get_conversation_service()
    conv = service.get_conversation_with_messages(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    phone = conv["phone"]
    whatsapp = get_whatsapp_service()

    wa_message_id = None
    try:
        wa_log(logger, "ADMIN SEND", f"to +{phone}: {text[:80]}")
        graph_response = await whatsapp.send_text(phone, text)
        wa_message_id = whatsapp.extract_sent_message_id(graph_response)
        if wa_message_id:
            wa_log(logger, "META ACCEPTED", f"wamid={wa_message_id} → +{phone}")
    except ValueError as exc:
        wa_log(logger, "ADMIN SEND FAILED", str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        wa_log(logger, "ADMIN SEND FAILED", str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    service.save_message(conversation_id, "assistant", text)
    return {"status": "sent", "phone": phone, "whatsapp_message_id": wa_message_id}
