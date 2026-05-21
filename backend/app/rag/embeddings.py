"""OpenAI embedding generation — with TTLCache to avoid re-embedding repeated queries."""

from openai import AsyncOpenAI, OpenAI

from app.cache import cache_get, cache_set, embedding_cache
from app.core.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._async_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

    def embed_text(self, text: str) -> list[float]:
        key = f"{self._model}:{text[:500]}"
        hit, cached = cache_get(embedding_cache, key)
        if hit:
            return cached  # type: ignore[return-value]

        response = self._client.embeddings.create(
            input=text,
            model=self._model,
            dimensions=self._dimensions,
        )
        vector = response.data[0].embedding
        cache_set(embedding_cache, key, vector)
        return vector

    async def embed_text_async(self, text: str) -> list[float]:
        """Async embed — does not block the event loop."""
        key = f"{self._model}:{text[:500]}"
        hit, cached = cache_get(embedding_cache, key)
        if hit:
            return cached  # type: ignore[return-value]

        response = await self._async_client.embeddings.create(
            input=text,
            model=self._model,
            dimensions=self._dimensions,
        )
        vector = response.data[0].embedding
        cache_set(embedding_cache, key, vector)
        return vector

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(
            input=texts,
            model=self._model,
            dimensions=self._dimensions,
        )
        return [item.embedding for item in response.data]
