"""Select RAG backend: Pinecone (existing index) or Supabase pgvector."""

from supabase import Client

from app.core.config import Settings
from app.rag.embeddings import EmbeddingService
from app.rag.pinecone_retriever import PineconeRetriever
from app.rag.retriever import SupabaseRetriever


def get_retriever(db: Client, settings: Settings, embeddings: EmbeddingService):
    provider = settings.rag_provider.lower().strip()
    if provider == "pinecone":
        return PineconeRetriever(settings, embeddings)
    if provider == "supabase":
        return SupabaseRetriever(db, embeddings)
    raise ValueError(f"Unknown RAG_PROVIDER: {provider}. Use 'pinecone' or 'supabase'.")
