"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "WhatsApp AI Chatbot"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # WhatsApp Cloud API
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    verify_token: str = Field(
        default="",
        validation_alias=AliasChoices("VERIFY_TOKEN", "WEBHOOK_VERIFY_TOKEN"),
    )
    app_secret: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""

    # Organization (single-tenant default)
    default_organization_id: str = ""

    # RAG — pinecone = your existing index; supabase = upload to DB
    rag_provider: str = "pinecone"
    rag_top_k: int = 5
    rag_min_similarity: float = 0.35
    conversation_history_limit: int = 10

    # Pinecone (existing RAG project)
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""
    pinecone_host: str = ""
    pinecone_namespace: str = ""
    pinecone_text_metadata_key: str = "text"

    # Company branding (overridden by DB settings)
    company_name: str = "Our Company"


@lru_cache
def get_settings() -> Settings:
    return Settings()
