"""Vector retrieval from existing Pinecone index."""

from uuid import UUID

from pinecone import Pinecone

from app.core.config import Settings
from app.rag.embeddings import EmbeddingService


class PineconeRetriever:
    """Query an existing Pinecone index (your prior RAG project)."""

    def __init__(self, settings: Settings, embedding_service: EmbeddingService) -> None:
        if not settings.pinecone_api_key:
            raise RuntimeError("PINECONE_API_KEY is required when RAG_PROVIDER=pinecone")

        self._embeddings = embedding_service
        self._top_k = settings.rag_top_k
        self._min_similarity = settings.rag_min_similarity
        self._text_field = settings.pinecone_text_metadata_key

        # Support PINECONE_NAMESPACES (comma-separated) or fallback to single PINECONE_NAMESPACE
        # "__default__" is treated as the default (no namespace) namespace
        def _parse_ns(raw: str) -> str | None:
            s = raw.strip()
            return None if s in ("", "__default__") else s

        if settings.pinecone_namespaces:
            self._namespaces = [_parse_ns(n) for n in settings.pinecone_namespaces.split(",") if n.strip()]
        elif settings.pinecone_namespace:
            self._namespaces = [_parse_ns(settings.pinecone_namespace)]
        else:
            self._namespaces = [None]  # query default namespace

        pc = Pinecone(api_key=settings.pinecone_api_key)
        if settings.pinecone_host:
            self._index = pc.Index(host=settings.pinecone_host)
        elif settings.pinecone_index_name:
            # Resolve host from index name (serverless / pod indexes)
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

    def retrieve(
        self,
        query: str,
        organization_id: UUID | None = None,
        top_k: int | None = None,
    ) -> list[dict]:
        del organization_id  # optional: use PINECONE_NAMESPACE per tenant later

        vector = self._embeddings.embed_text(query)
        k = top_k or self._top_k
        all_chunks: list[dict] = []

        for namespace in self._namespaces:
            kwargs: dict = {
                "vector": vector,
                "top_k": k,
                "include_metadata": True,
            }
            if namespace:
                kwargs["namespace"] = namespace

            response = self._index.query(**kwargs)

            for match in response.matches:
                if self._min_similarity and float(match.score or 0) < self._min_similarity:
                    continue
                meta = match.metadata or {}
                text = (
                    meta.get(self._text_field)
                    or meta.get("text")
                    or meta.get("content")
                    or meta.get("chunk_text")
                    or meta.get("page_content")
                )
                if text:
                    all_chunks.append(
                        {
                            "chunk_text": str(text),
                            "similarity": float(match.score or 0),
                        }
                    )

        # Sort by similarity descending, return top_k best across all namespaces
        all_chunks.sort(key=lambda x: x["similarity"], reverse=True)
        return all_chunks[:k]
