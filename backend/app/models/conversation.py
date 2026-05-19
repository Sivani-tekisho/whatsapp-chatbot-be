"""Conversation Pydantic models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationBase(BaseModel):
    phone: str
    status: str = "active"


class Conversation(ConversationBase):
    id: UUID
    organization_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    message_count: int | None = None
    last_message: str | None = None


class ConversationListResponse(BaseModel):
    items: list[Conversation]
    total: int


class ConversationDetail(Conversation):
    messages: list["MessageResponse"] = []


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    message: str
    timestamp: datetime | None = None


class DashboardMetrics(BaseModel):
    total_conversations: int
    messages_today: int
    resolved_conversations: int
    average_response_time_seconds: float
