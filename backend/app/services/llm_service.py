"""OpenAI LLM integration."""

import logging

from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.logging_config import wa_log

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = (settings.openai_model or "gpt-4o-mini").strip()
        self._max_tokens = settings.openai_max_tokens

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, messages: list[dict]) -> str:
        wa_log(
            logger,
            "LLM CALL",
            f"model={self._model} messages={len(messages)} max_tokens={self._max_tokens or 'default'}",
        )
        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.2,
        }
        if self._max_tokens > 0:
            kwargs["max_tokens"] = self._max_tokens
        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        return (content or "").strip()
