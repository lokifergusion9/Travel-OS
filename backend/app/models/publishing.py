"""Publishing models (Module 4): social accounts and scheduled posts.

Tenant-scoped (RLS). Access tokens are stored encrypted (Fernet).
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, TimestampMixin, UUIDPrimaryKey

POST_STATUSES = ("scheduled", "publishing", "published", "failed")


class SocialAccount(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "social_accounts"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="instagram")
    account_name: Mapped[str] = mapped_column(String(160), nullable=False)
    ig_user_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    access_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    connected: Mapped[bool] = mapped_column(Boolean, default=True)
    is_dev: Mapped[bool] = mapped_column(Boolean, default=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class ScheduledPost(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "scheduled_posts"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    social_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("social_accounts.id", ondelete="SET NULL"), nullable=True
    )
    trip_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    creative_asset_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="scheduled", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
