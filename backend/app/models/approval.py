"""Human-in-the-loop approval queue (cross-cutting). Tenant-scoped (RLS).

Every agent action that publishes/sends/finalises drops a row here in
``pending`` state; the Approval Center surfaces them for a human decision.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, TimestampMixin, UUIDPrimaryKey

APPROVAL_STATUSES = ("pending", "approved", "rejected")


class Approval(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "approvals"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    # e.g. "itinerary", "creative" — which agent/output this gates.
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    trip_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
