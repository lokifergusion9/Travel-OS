"""Trip / itinerary / creative / approval schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TripCreate(BaseModel):
    destination: str = Field(min_length=2, max_length=160)
    days: int = Field(ge=1, le=30, default=3)
    audience: str | None = Field(default=None, max_length=120)
    season: str | None = Field(default=None, max_length=60)
    budget_per_person: int | None = Field(default=None, ge=0)


class ItineraryDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day_number: int
    title: str
    summary: str | None
    activities: list[Any]
    stay: str | None
    transport: str | None


class CostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: str
    per_person: int | None
    breakdown: list[Any]


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    destination: str
    days: int
    audience: str | None
    season: str | None
    budget_per_person: int | None
    status: str
    overview: str | None
    created_at: datetime


class TripDetail(TripOut):
    days_plan: list[ItineraryDayOut] = []
    costing: CostingOut | None = None


class CreativeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_id: uuid.UUID | None
    kind: str
    status: str
    url: str | None
    text_content: str | None
    meta: dict[str, Any]
    created_at: datetime


class CreativeRequest(BaseModel):
    kinds: list[str] = Field(default_factory=lambda: ["poster", "caption", "brochure"])


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    entity_type: str
    entity_id: uuid.UUID
    trip_id: uuid.UUID | None
    title: str
    summary: str | None
    status: str
    payload: dict[str, Any]
    created_at: datetime


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
