"""Creative Studio assets (Module 2). Tenant-scoped (RLS)."""
import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, TimestampMixin, UUIDPrimaryKey

CREATIVE_KINDS = ("poster", "caption", "brochure", "reel")
CREATIVE_STATUSES = ("pending_review", "approved", "rejected")


class CreativeAsset(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "creative_assets"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_review")
    # For poster/brochure: a served URL. For caption: text_content holds the copy.
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
