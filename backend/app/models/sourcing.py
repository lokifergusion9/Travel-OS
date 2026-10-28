"""Sourcing models (Module 3): vendors and deals. Tenant-scoped (RLS)."""
import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, TimestampMixin, UUIDPrimaryKey

VENDOR_TYPES = ("hotel", "transport", "activity")
DEAL_STATUSES = ("requested", "negotiating", "confirmed", "declined")


class Vendor(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "vendors"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="hotel")
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Deal(Base, UUIDPrimaryKey, TimestampMixin):
    """A sourcing conversation with a vendor for a trip, with embedded outreach."""

    __tablename__ = "deals"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=True, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="hotel")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="requested")
    outreach_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    outreach_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent: Mapped[bool] = mapped_column(default=False)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
