"""RAG orchestration layer — Pinecone (existing index) or Supabase pgvector.

retrieve_context() results are cached in a TTLCache (10 min) keyed by query text
so identical/repeated queries never hit Pinecone + OpenAI twice.
"""

import asyncio
import hashlib
import json
import logging
from uuid import UUID

from supabase import Client

from app.cache import cache_get, cache_set, rag_cache, rag_result_cache
from app.core.config import Settings
from app.core.logging_config import wa_log
from app.rag.embeddings import EmbeddingService
from app.rag.chunk_guard import filter_company_chunks
from app.rag.retriever_factory import get_retriever

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, db: Client, settings: Settings) -> None:
        embeddings = EmbeddingService(settings)
        self._db = db
        self._settings = settings
        self._retriever = get_retriever(db, settings, embeddings)
        self._top_k = settings.rag_top_k
        self._org_id = settings.default_organization_id
        self._provider = settings.rag_provider.lower()

    def _resolve_org_id(self, db: Client) -> UUID | None:
        if self._org_id:
            return UUID(self._org_id)
        org = db.table("organizations").select("id").limit(1).execute()
        if not org.data:
            return None
        return UUID(org.data[0]["id"])

    def retrieve_context(self, query: str, db: Client | None = None) -> list[str]:
        key = f"rag:{query[:300]}"
        hit, cached = cache_get(rag_cache, key)
        if hit:
            wa_log(logger, "CACHE HIT", f"RAG chunks for: {query[:60]!r}")
            return cached  # type: ignore[return-value]

        wa_log(logger, "CACHE MISS", f"RAG → Pinecone query: {query[:60]!r}")
        client = db or self._db
        org_id = self._resolve_org_id(client) if self._provider == "supabase" else None
        chunks = self._retriever.retrieve(query, org_id, self._top_k)
        min_score = self._settings.rag_min_similarity
        texts = [
            c["chunk_text"]
            for c in chunks
            if c.get("chunk_text") and float(c.get("similarity", 0)) >= min_score
        ]
        result = filter_company_chunks(texts, enabled=self._settings.rag_filter_off_topic)
        cache_set(rag_cache, key, result)
        return result

    async def retrieve_context_async(self, query: str) -> list[str]:
        """Async version — uses AsyncOpenAI embed, no asyncio.to_thread needed."""
        key = f"rag:{query[:300]}"
        hit, cached = cache_get(rag_cache, key)
        if hit:
            wa_log(logger, "CACHE HIT", f"RAG async chunks for: {query[:60]!r}")
            return cached  # type: ignore[return-value]

        wa_log(logger, "CACHE MISS", f"RAG async -> Pinecone query: {query[:60]!r}")
        # Async embed — does not block the event loop
        vector = await self._retriever._embeddings.embed_text_async(query)

        # Vector-level cache: skip Pinecone if we've seen this vector before
        vec_key = hashlib.md5(json.dumps(vector[:8]).encode()).hexdigest()
        if vec_key in rag_result_cache:
            wa_log(logger, "CACHE HIT", "RAG vector cache hit")
            cached_chunks = rag_result_cache[vec_key]
            cache_set(rag_cache, key, cached_chunks)
            return cached_chunks

        # Pinecone query in a thread (network I/O — keeps event loop free)
        chunks = await asyncio.to_thread(
            self._retriever._query_all_namespaces, vector, self._top_k
        )
        min_score = self._settings.rag_min_similarity
        texts = [
            c["chunk_text"]
            for c in chunks
            if c.get("chunk_text") and float(c.get("similarity", 0)) >= min_score
        ]
        result = filter_company_chunks(texts, enabled=self._settings.rag_filter_off_topic)
        cache_set(rag_cache, key, result)
        rag_result_cache[vec_key] = result
        return result

    def has_relevant_context(self, chunks: list[str]) -> bool:
        return len(chunks) > 0
