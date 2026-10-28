"""Sourcing (vendors, deals) schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.sourcing import DEAL_STATUSES, VENDOR_TYPES


class VendorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: str = Field(default="hotel", pattern="^(" + "|".join(VENDOR_TYPES) + ")$")
    location: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: str
    location: str | None
    contact_email: str | None
    contact_phone: str | None
    notes: str | None


class DealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_id: uuid.UUID | None
    vendor_id: uuid.UUID
    kind: str
    status: str
    outreach_subject: str | None
    outreach_body: str | None
    sent: bool
    terms: str | None
    amount: int | None
    currency: str
    created_at: datetime


class DealUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(" + "|".join(DEAL_STATUSES) + ")$")
    terms: str | None = None
    amount: int | None = None
