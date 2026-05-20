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
    # 0 = model default (no artificial cap)
    openai_max_tokens: int = 0
    whatsapp_use_compact_prompt: bool = True
    # False = include full DB system_prompt + compact/file template on RAG replies
    whatsapp_rag_minimal_system: bool = False
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

    # WhatsApp template for first contact to new users (Meta-approved)
    whatsapp_welcome_template_name: str = Field(
        default="welcome_messages",
        validation_alias=AliasChoices(
            "WHATSAPP_WELCOME_TEMPLATE_NAME",
            "WHATSAPP_TEMPLATE_NAME",
        ),
    )
    whatsapp_welcome_template_language: str = Field(
        default="en",
        validation_alias=AliasChoices(
            "WHATSAPP_WELCOME_TEMPLATE_LANGUAGE",
            "WHATSAPP_TEMPLATE_LANGUAGE",
        ),
    )
    # Comma-separated values for {{1}}, {{2}}, … in the welcome template body
    whatsapp_welcome_template_body_params: str = Field(
        default="",
        validation_alias=AliasChoices("WHATSAPP_WELCOME_TEMPLATE_BODY_PARAMS"),
    )

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""

    # Organization (single-tenant default)
    default_organization_id: str = ""

    # RAG — pinecone = your existing index; supabase = upload to DB
    rag_provider: str = "pinecone"
    rag_top_k: int = 8
    rag_min_similarity: float = 0.35
    # 0 = do not truncate retrieved chunks
    rag_chunk_max_chars: int = 0
    rag_filter_off_topic: bool = False
    # 0 = load full conversation history for the LLM
    conversation_history_limit: int = 0

    # Pinecone (existing RAG project)
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""
    pinecone_host: str = ""
    pinecone_namespace: str = ""
    # Comma-separated Pinecone namespaces (used when pinecone_namespace is empty)
    pinecone_namespaces: str = "__default__,vocalq,leadq,emailq"
    pinecone_text_metadata_key: str = "text"

    # Company branding (overridden by DB / .env; see app.company_branding for file defaults)
    company_name: str = ""
    # Public contact info for WhatsApp system prompt (see app/prompts/whatsapp_system_prompt.txt)
    website_url: str = Field(default="", validation_alias=AliasChoices("WEBSITE_URL", "COMPANY_WEBSITE_URL"))
    support_email: str = Field(default="", validation_alias=AliasChoices("SUPPORT_EMAIL", "COMPANY_SUPPORT_EMAIL"))
    sales_email: str = Field(default="", validation_alias=AliasChoices("SALES_EMAIL", "COMPANY_SALES_EMAIL"))
    company_phone: str = Field(default="", validation_alias=AliasChoices("PHONE_NUMBER", "COMPANY_PHONE"))
    company_whatsapp_display: str = Field(
        default="",
        validation_alias=AliasChoices("WHATSAPP_NUMBER", "COMPANY_WHATSAPP_NUMBER", "COMPANY_WHATSAPP_DISPLAY"),
    )
    office_address: str = Field(default="", validation_alias=AliasChoices("OFFICE_ADDRESS", "COMPANY_OFFICE_ADDRESS"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
