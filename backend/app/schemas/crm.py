"""CRM (leads, messages, templates) schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.lead import LEAD_STAGES


class LeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    source: str = "manual"
    trip_id: uuid.UUID | None = None
    notes: str | None = None


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    source: str
    stage: str
    score: int
    trip_id: uuid.UUID | None
    notes: str | None
    last_contacted_at: datetime | None
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: str
    direction: str
    subject: str | None
    body: str
    status: str
    created_at: datetime


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    content: str | None
    meta: dict[str, Any]
    created_at: datetime


class LeadDetail(LeadOut):
    messages: list[MessageOut] = []
    activities: list[ActivityOut] = []


class StageUpdate(BaseModel):
    stage: str = Field(pattern="^(" + "|".join(LEAD_STAGES) + ")$")


class ReplyIn(BaseModel):
    body: str = Field(min_length=1)
    channel: str = "email"


class InboundIn(BaseModel):
    body: str = Field(min_length=1)
    channel: str = "email"


class CaptureIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr | None = None
    phone: str | None = None
    trip_id: uuid.UUID | None = None
    message: str | None = None


class TemplateCreate(BaseModel):
    name: str
    channel: str = "email"
    subject: str | None = None
    body: str
    step: int = 0


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    channel: str
    subject: str | None
    body: str
    step: int
