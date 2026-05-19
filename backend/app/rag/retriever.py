"""Vector retrieval via Supabase pgvector RPC (optional upload path)."""

from uuid import UUID

from supabase import Client

from app.rag.embeddings import EmbeddingService


class SupabaseRetriever:
    def __init__(self, db: Client, embedding_service: EmbeddingService) -> None:
        self._db = db
        self._embeddings = embedding_service

    def retrieve(
        self,
        query: str,
        organization_id: UUID,
        top_k: int = 5,
    ) -> list[dict]:
        query_embedding = self._embeddings.embed_text(query)

        result = self._db.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "org_id": str(organization_id),
            },
        ).execute()

        return result.data or []
