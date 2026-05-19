"""Organization Pydantic models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    name: str
    bot_name: str = "Company Assistant"
    system_prompt: str | None = None
    greeting_message: str = "Hello! How can I help you today?"
    fallback_message: str = "I couldn't find that information."


class OrganizationUpdate(BaseModel):
    name: str | None = None
    bot_name: str | None = None
    system_prompt: str | None = None
    greeting_message: str | None = None
    fallback_message: str | None = None


class Organization(OrganizationBase):
    id: UUID
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class OrganizationSettingsResponse(Organization):
    company_name: str = Field(alias="name")
