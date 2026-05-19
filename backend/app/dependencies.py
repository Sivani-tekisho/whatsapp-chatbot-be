"""Dependency injection container for services."""

from functools import lru_cache

from app.agents.company_agent import CompanyAgent
from app.core.config import Settings, get_settings
from app.db.database import get_supabase_client
from app.rag.embeddings import EmbeddingService
from app.rag.ingest import DocumentIngestor
from app.services.conversation_service import ConversationService
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.message_processor import MessageProcessor
from app.services.prompt_service import PromptService, get_prompt_service
from app.services.rag_service import RAGService
from app.services.whatsapp_service import WhatsAppService


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(get_settings())


@lru_cache
def get_document_ingestor() -> DocumentIngestor:
    return DocumentIngestor(get_supabase_client(), get_embedding_service())


def get_conversation_service(settings: Settings | None = None) -> ConversationService:
    return ConversationService(get_supabase_client(), settings or get_settings())


def get_memory_service(settings: Settings | None = None) -> MemoryService:
    return MemoryService(get_supabase_client(), settings or get_settings())


def get_rag_service(settings: Settings | None = None) -> RAGService:
    return RAGService(get_supabase_client(), settings or get_settings())


def get_llm_service(settings: Settings | None = None) -> LLMService:
    return LLMService(settings or get_settings())


def get_whatsapp_service(settings: Settings | None = None) -> WhatsAppService:
    return WhatsAppService(settings or get_settings())


def get_company_agent(settings: Settings | None = None) -> CompanyAgent:
    s = settings or get_settings()
    return CompanyAgent(
        settings=s,
        rag_service=get_rag_service(s),
        llm_service=get_llm_service(s),
        prompt_service=get_prompt_service(),
        memory_service=get_memory_service(s),
    )


def get_message_processor(settings: Settings | None = None) -> MessageProcessor:
    s = settings or get_settings()
    db = get_supabase_client()
    return MessageProcessor(
        db=db,
        settings=s,
        agent=get_company_agent(s),
        conversation_service=get_conversation_service(s),
        whatsapp_service=get_whatsapp_service(s),
    )
