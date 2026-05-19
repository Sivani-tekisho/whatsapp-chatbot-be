"""Document Pydantic models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class DocumentBase(BaseModel):
    title: str
    content: str | None = None
    source_type: str = "upload"
    source_url: str | None = None


class Document(DocumentBase):
    id: UUID
    organization_id: UUID
    created_at: datetime | None = None


class DocumentListResponse(BaseModel):
    items: list[Document]
    total: int


class UrlIngestRequest(BaseModel):
    url: HttpUrl
    title: str | None = None


class IngestResponse(BaseModel):
    document_id: UUID
    chunks_created: int
    message: str
