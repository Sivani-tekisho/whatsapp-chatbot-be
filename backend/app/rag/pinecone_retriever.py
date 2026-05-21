"""Vector retrieval from existing Pinecone index (multi-namespace)."""

from __future__ import annotations

import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID

from pinecone import Pinecone

from app.cache import rag_result_cache
from app.core.config import Settings
from app.rag.embeddings import EmbeddingService
from app.rag.namespace_router import (
    DEFAULT_NAMESPACE,
    namespaces_for_query,
    parse_namespace_list,
)

logger = logging.getLogger(__name__)


class PineconeRetriever:
    """Query an existing Pinecone index across Tekisho + product namespaces."""

    def __init__(self, settings: Settings, embedding_service: EmbeddingService) -> None:
        if not settings.pinecone_api_key:
            raise RuntimeError("PINECONE_API_KEY is required when RAG_PROVIDER=pinecone")

        self._embeddings = embedding_service
        self._top_k = settings.rag_top_k
        self._text_field = settings.pinecone_text_metadata_key

        # Single-namespace override (legacy) wins over multi-namespace list
        if settings.pinecone_namespace.strip():
            self._all_namespaces = [settings.pinecone_namespace.strip()]
        else:
            configured = parse_namespace_list(settings.pinecone_namespaces)
            self._all_namespaces = configured or [
                DEFAULT_NAMESPACE,
                "vocalq",
                "leadq",
                "emailq",
            ]

        pc = Pinecone(api_key=settings.pinecone_api_key)
        if settings.pinecone_host:
            self._index = pc.Index(host=settings.pinecone_host)
        elif settings.pinecone_index_name:
            desc = pc.describe_index(settings.pinecone_index_name)
            host = getattr(desc, "host", None) or (
                desc.get("host") if isinstance(desc, dict) else None
            )
            if host:
                self._index = pc.Index(host=host)
            else:
                self._index = pc.Index(settings.pinecone_index_name)
        else:
            raise RuntimeError("Set PINECONE_HOST or PINECONE_INDEX_NAME in .env")

    def _extract_text(self, metadata: dict) -> str | None:
        meta = metadata or {}
        text = (
            meta.get(self._text_field)
            or meta.get("text")
            or meta.get("content")
            or meta.get("chunk_text")
            or meta.get("page_content")
        )
        return str(text) if text else None

    def _query_namespace(
        self,
        vector: list[float],
        namespace: str,
        top_k: int,
    ) -> list[dict]:
        kwargs: dict = {
            "vector": vector,
            "top_k": top_k,
            "include_metadata": True,
            "namespace": namespace,
        }
        response = self._index.query(**kwargs)
        chunks: list[dict] = []
        for match in response.matches:
            text = self._extract_text(match.metadata or {})
            if not text:
                continue
            # Label product namespaces so the LLM knows which product the chunk is about
            if namespace != DEFAULT_NAMESPACE:
                text = f"[{namespace}] {text}"
            chunks.append(
                {
                    "chunk_text": text,
                    "similarity": float(match.score or 0),
                    "namespace": namespace,
                }
            )
        return chunks

    def retrieve(
        self,
        query: str,
        organization_id: UUID | None = None,
        top_k: int | None = None,
    ) -> list[dict]:
        del organization_id

        limit = top_k or self._top_k
        target_namespaces = namespaces_for_query(query, self._all_namespaces)

        if len(self._all_namespaces) == 1:
            target_namespaces = self._all_namespaces

        logger.debug(
            "Pinecone RAG query namespaces=%s (configured=%s)",
            target_namespaces,
            self._all_namespaces,
        )

        vector = self._embeddings.embed_text(query)
        per_ns_k = limit

        # ── Embedding-vector cache (skip Pinecone if we've seen this vector) ─
        _vec_key = hashlib.md5(json.dumps(vector[:8]).encode()).hexdigest()
        if _vec_key in rag_result_cache:
            logger.info("[RAG] Cache hit — skipping Pinecone query")
            return rag_result_cache[_vec_key]

        merged: list[dict] = []
        workers = min(4, len(target_namespaces))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._query_namespace, vector, ns, per_ns_k): ns
                for ns in target_namespaces
            }
            for future in as_completed(futures):
                merged.extend(future.result())

        merged.sort(key=lambda c: c["similarity"], reverse=True)

        seen_text: set[str] = set()
        unique: list[dict] = []
        for chunk in merged:
            key = chunk["chunk_text"][:200]
            if key in seen_text:
                continue
            seen_text.add(key)
            unique.append(chunk)
            if len(unique) >= limit:
                break

        rag_result_cache[_vec_key] = unique
        return unique

    def _query_all_namespaces(self, vector: list[float], top_k: int) -> list[dict]:
        """Query Pinecone with a pre-computed vector (no embed step).
        Used by retrieve_context_async() so embed and Pinecone can overlap.
        Queries only __default__ namespace for speed (4x faster than 4 namespaces).
        """
        return self._query_namespace(vector, DEFAULT_NAMESPACE, top_k)
