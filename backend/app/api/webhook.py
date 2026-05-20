"""WhatsApp webhook endpoints."""

import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response

from app.core.config import get_settings
from app.core.logging_config import wa_log
from app.core.security import verify_webhook_signature
from app.dependencies import get_message_processor
from app.services.webhook_activity import log_event
from app.services.webhook_dedup import is_duplicate_message
from app.services.whatsapp_service import normalize_whatsapp_recipient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhook"])


def _extract_incoming_message(body: dict) -> list[dict]:
    messages = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                text = msg.get("text", {}).get("body", "")
                try:
                    phone = normalize_whatsapp_recipient(msg.get("from", ""))
                except ValueError:
                    continue
                if phone and text:
                    messages.append(
                        {
                            "phone": phone,
                            "text": text,
                            "message_id": msg.get("id"),
                        }
                    )
    return messages


@router.get("/webhook")
@router.get("/webhook/", include_in_schema=False)
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    wa_log(
        logger,
        "META VERIFY HIT",
        f"mode={hub_mode!r} token_match_pending",
    )
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.verify_token:
        log_event("GET", "Meta webhook verification OK")
        wa_log(logger, "META VERIFY OK", "Callback URL accepted by Meta (GET only — not a user message)")
        return Response(content=hub_challenge, media_type="text/plain")

    log_event("GET", "Verification FAILED — token mismatch")
    wa_log(logger, "META VERIFY FAILED", "Check WEBHOOK_VERIFY_TOKEN matches Meta dashboard")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    settings = get_settings()
    raw_body = await request.body()

    wa_log(logger, "INBOUND POST", "Meta sent a webhook event to /webhook")

    signature = request.headers.get("X-Hub-Signature-256")
    if settings.app_secret and not verify_webhook_signature(
        raw_body, signature, settings.app_secret
    ):
        wa_log(logger, "INBOUND REJECTED", "Invalid APP_SECRET signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        wa_log(logger, "INBOUND REJECTED", "Invalid JSON body")
        return {"status": "ok"}

    if body.get("object") != "whatsapp_business_account":
        log_event("POST", f"Ignored object={body.get('object')}")
        wa_log(logger, "INBOUND IGNORED", f"Not WhatsApp payload (object={body.get('object')})")
        return {"status": "ignored"}

    incoming = _extract_incoming_message(body)

    if not incoming:
        log_event("POST", "No text message in payload (status/update?)")
        wa_log(logger, "INBOUND POST", "No user text — subscribe to 'messages' field in Meta")
        return {"status": "ok"}

    for msg in incoming:
        log_event("POST", f"User said: {msg['text'][:80]}", phone=msg["phone"])
        wa_log(logger, "USER MESSAGE", f"from +{msg['phone']}: {msg['text'][:100]}")

    processor = get_message_processor()
    for msg in incoming:
        mid = msg.get("message_id")
        if is_duplicate_message(mid):
            wa_log(logger, "INBOUND SKIP", f"Duplicate message_id={mid}")
            continue
        background_tasks.add_task(
            _process_message_safe,
            processor,
            msg["phone"],
            msg["text"],
            mid,
        )

    return {"status": "ok"}


async def _process_message_safe(processor, phone: str, text: str, message_id: str | None) -> None:
    try:
        wa_log(logger, "PROCESSING", f"+{phone}")
        await processor.process_message(phone, text, message_id)
        wa_log(logger, "REPLY SENT", f"+{phone}")
    except Exception as exc:
        wa_log(logger, "PROCESSING FAILED", f"+{phone} | {exc}")
        logger.exception("Full error for +%s", phone)
