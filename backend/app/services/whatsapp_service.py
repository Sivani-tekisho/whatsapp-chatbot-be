"""Meta WhatsApp Cloud API client."""

import httpx

from app.core.config import Settings


def normalize_whatsapp_recipient(phone: str) -> str:
    """Meta expects digits only with country code, e.g. 919876543210 (no + or spaces)."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        raise ValueError(f"Invalid WhatsApp recipient phone: {phone!r}")
    return digits


def format_graph_api_error(response: httpx.Response) -> str:
    """Turn Meta Graph error JSON into a short message for logs and admin UI."""
    try:
        err = response.json().get("error", {})
        parts = [err.get("message") or response.text]
        if err.get("code"):
            parts.append(f"code={err['code']}")
        if err.get("error_subcode"):
            parts.append(f"subcode={err['error_subcode']}")
        hint = _hint_for_meta_error(err)
        if hint:
            parts.append(hint)
        return " | ".join(p for p in parts if p)
    except Exception:
        return response.text or f"HTTP {response.status_code}"


def _hint_for_meta_error(err: dict) -> str | None:
    code = err.get("code")
    sub = err.get("error_subcode")
    if code == 100 or sub == 33:
        return (
            "Use WHATSAPP_ACCESS_TOKEN from Meta → WhatsApp → API Setup "
            "(not Graph API Explorer user token)"
        )
    if code == 131030:
        return "Add recipient in Meta → WhatsApp → API Setup → test phone list"
    if code in (131047, 131051):
        return "Outside 24h window: user must message first or use approved template"
    if code == 131026:
        return "Recipient is not a valid WhatsApp number"
    return None


class WhatsAppService:
    BASE_URL = "https://graph.facebook.com/v21.0"

    def __init__(self, settings: Settings) -> None:
        self._token = settings.whatsapp_access_token
        self._phone_id = settings.whatsapp_phone_number_id

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _post_messages(self, payload: dict) -> dict:
        if not self._token or not self._phone_id:
            raise ValueError(
                "WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID must be set in backend/.env"
            )
        url = f"{self.BASE_URL}/{self._phone_id}/messages"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self._headers())
            if response.is_success:
                return response.json()
            raise httpx.HTTPStatusError(
                format_graph_api_error(response),
                request=response.request,
                response=response,
            )

    async def send_text(self, to: str, text: str) -> dict:
        recipient = normalize_whatsapp_recipient(to)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text[:4096]},
        }
        return await self._post_messages(payload)

    async def mark_as_read(self, message_id: str) -> None:
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        try:
            await self._post_messages(payload)
        except Exception:
            # Read receipt failure must not block the reply
            pass
