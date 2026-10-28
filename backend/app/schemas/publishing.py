"""Publishing (social accounts, scheduled posts) schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConnectDevIn(BaseModel):
    account_name: str = Field(min_length=1, max_length=160, default="@my_agency")


class SocialAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: str
    account_name: str
    ig_user_id: str | None
    connected: bool
    is_dev: bool


class PostCreate(BaseModel):
    caption: str = ""
    image_url: str | None = None
    creative_asset_id: uuid.UUID | None = None
    social_account_id: uuid.UUID | None = None
    trip_id: uuid.UUID | None = None
    scheduled_at: datetime | None = None


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    social_account_id: uuid.UUID | None
    trip_id: uuid.UUID | None
    image_url: str | None
    caption: str | None
    status: str
    scheduled_at: datetime | None
    published_at: datetime | None
    result: dict[str, Any]
    created_at: datetime
