"""OpenAI LLM integration."""

import logging
from collections.abc import Awaitable, Callable

from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.logging_config import wa_log

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, settings: Settings) -> None:
        # 10s timeout — prevents 20s+ hangs on slow OpenAI responses
        self._client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=10.0)
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
            "temperature": 0.8,
        }
        if self._max_tokens > 0:
            kwargs["max_tokens"] = self._max_tokens
        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        return (content or "").strip()

    async def generate_streaming(self, messages: list[dict]) -> str:
        """Stream from OpenAI and collect full reply (no progressive send).
        Falls back to generate() if streaming fails.
        """
        wa_log(
            logger,
            "LLM STREAM",
            f"model={self._model} messages={len(messages)} max_tokens={self._max_tokens or 'default'}",
        )
        try:
            collected: list[str] = []
            kwargs: dict = {
                "model": self._model,
                "messages": messages,
                "temperature": 0,
                "stream": True,
            }
            if self._max_tokens > 0:
                kwargs["max_tokens"] = self._max_tokens
            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    collected.append(delta)
            return "".join(collected).strip()
        except Exception as exc:
            logger.warning("[LLM] Streaming failed, falling back to non-streaming: %s", exc)
            return await self.generate(messages)

    async def stream_to_sender(
        self,
        messages: list[dict],
        send_chunk_fn: Callable[[str], Awaitable[None]],
    ) -> str:
        """Stream tokens from OpenAI (keeps connection alive, avoids timeouts)
        then delivers the COMPLETE reply as a single call to send_chunk_fn.

        One WhatsApp bubble. Returns full text for DB saving.
        Falls back to generate() + single send on any error.
        """
        wa_log(
            logger,
            "LLM STREAM",
            f"model={self._model} messages={len(messages)} max_tokens={self._max_tokens or 'default'}",
        )
        try:
            kwargs: dict = {
                "model": self._model,
                "messages": messages,
                "temperature": 0.8,
                "stream": True,
            }
            if self._max_tokens > 0:
                kwargs["max_tokens"] = self._max_tokens

            tokens: list[str] = []
            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    tokens.append(delta)

            full_text = "".join(tokens).strip()
            wa_log(logger, "LLM DONE", f"chars={len(full_text)}")

            # Send the complete reply as ONE message
            if full_text:
                await send_chunk_fn(full_text)
            return full_text

        except Exception as exc:
            logger.warning("[LLM] Streaming failed, falling back: %s", exc)
            full_text = await self.generate(messages)
            if full_text:
                await send_chunk_fn(full_text)
            return full_text
