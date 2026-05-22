"""OpenAI embedding generation."""

import time

from openai import OpenAI

from app.core.config import Settings

_EMBED_CACHE: dict[str, tuple[list[float], float]] = {}
_EMBED_CACHE_TTL = 3600.0


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

    def embed_text(self, text: str) -> list[float]:
        key = (text or "").strip().lower()
        now = time.time()
        if key:
            hit = _EMBED_CACHE.get(key)
            if hit and now < hit[1]:
                return hit[0]
        response = self._client.embeddings.create(
            input=text,
            model=self._model,
            dimensions=self._dimensions,
        )
        vector = response.data[0].embedding
        if key:
            _EMBED_CACHE[key] = (vector, now + _EMBED_CACHE_TTL)
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
