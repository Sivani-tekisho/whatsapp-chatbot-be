"""Message Pydantic models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MessageCreate(BaseModel):
    conversation_id: UUID
    role: str
    message: str


class Message(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    message: str
    timestamp: datetime | None = None
