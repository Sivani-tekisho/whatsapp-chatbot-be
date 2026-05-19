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
        self._namespace = settings.pinecone_namespace or None
        self._text_field = settings.pinecone_text_metadata_key

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
        kwargs: dict = {
            "vector": vector,
            "top_k": top_k or self._top_k,
            "include_metadata": True,
        }
        if self._namespace:
            kwargs["namespace"] = self._namespace

        response = self._index.query(**kwargs)

        chunks: list[dict] = []
        for match in response.matches:
            meta = match.metadata or {}
            text = (
                meta.get(self._text_field)
                or meta.get("text")
                or meta.get("content")
                or meta.get("chunk_text")
                or meta.get("page_content")
            )
            if text:
                chunks.append(
                    {
                        "chunk_text": str(text),
                        "similarity": float(match.score or 0),
                    }
                )
        return chunks
