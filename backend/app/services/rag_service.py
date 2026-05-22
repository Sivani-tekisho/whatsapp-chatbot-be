"""RAG orchestration layer — Pinecone (existing index) or Supabase pgvector."""

from uuid import UUID

from supabase import Client

from app.core.config import Settings
from app.rag.embeddings import EmbeddingService
from app.rag.chunk_guard import filter_company_chunks
from app.rag.retriever_factory import get_retriever


class RAGService:
    def __init__(
        self, db: Client, settings: Settings, embeddings: EmbeddingService | None = None
    ) -> None:
        emb = embeddings or EmbeddingService(settings)
        self._db = db
        self._settings = settings
        self._retriever = get_retriever(db, settings, emb)
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
        client = db or self._db
        org_id = self._resolve_org_id(client) if self._provider == "supabase" else None
        chunks = self._retriever.retrieve(query, org_id, self._top_k)
        min_score = self._settings.rag_min_similarity
        texts = [
            c["chunk_text"]
            for c in chunks
            if c.get("chunk_text") and float(c.get("similarity", 0)) >= min_score
        ]
        return filter_company_chunks(texts, enabled=self._settings.rag_filter_off_topic)

    def has_relevant_context(self, chunks: list[str]) -> bool:
        return len(chunks) > 0
