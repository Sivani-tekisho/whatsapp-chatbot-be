"""Conversation management API."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging_config import wa_log
from app.dependencies import get_conversation_service, get_whatsapp_service
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
):
    service = get_conversation_service()
    items, total = service.list_conversations(search, status, limit, offset)
    return ConversationListResponse(
        items=[Conversation(**c) for c in items],
        total=total,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: UUID):
    service = get_conversation_service()
    data = service.get_conversation_with_messages(conversation_id)
    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = [MessageResponse(**m) for m in data.pop("messages", [])]
    return ConversationDetail(**data, messages=messages)


class StatusUpdate(BaseModel):
    status: str


@router.patch("/{conversation_id}/status")
async def update_conversation_status(conversation_id: UUID, body: StatusUpdate):
    if body.status not in ("active", "resolved"):
        raise HTTPException(status_code=400, detail="Invalid status")
    service = get_conversation_service()
    return service.update_status(conversation_id, body.status)


class SendReplyBody(BaseModel):
    message: str


@router.post("/{conversation_id}/reply")
async def send_reply(conversation_id: UUID, body: SendReplyBody):
    """Send a WhatsApp text reply from admin (outbound via Meta API)."""
    text = body.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    service = get_conversation_service()
    conv = service.get_conversation_with_messages(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    phone = conv["phone"]
    whatsapp = get_whatsapp_service()

    try:
        wa_log(logger, "ADMIN SEND", f"to +{phone}: {text[:80]}")
        await whatsapp.send_text(phone, text)
    except ValueError as exc:
        wa_log(logger, "ADMIN SEND FAILED", str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        wa_log(logger, "ADMIN SEND FAILED", str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    service.save_message(conversation_id, "assistant", text)
    return {"status": "sent", "phone": phone}
