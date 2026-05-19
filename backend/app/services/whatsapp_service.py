"""Meta WhatsApp Cloud API client."""

import httpx

from app.core.config import Settings


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

    async def send_text(self, to: str, text: str) -> dict:
        url = f"{self.BASE_URL}/{self._phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text[:4096]},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def mark_as_read(self, message_id: str) -> None:
        url = f"{self.BASE_URL}/{self._phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(url, json=payload, headers=self._headers())
