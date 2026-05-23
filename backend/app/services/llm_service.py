"""OpenAI LLM integration."""

from openai import AsyncOpenAI

from app.core.config import Settings


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def generate(self, messages: list[dict]) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.3,
            max_tokens=512,
        )
        content = response.choices[0].message.content
        return (content or "").strip()
