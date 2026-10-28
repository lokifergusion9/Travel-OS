"""CRM models (Module 5): leads, activities, messages, templates, followups.

All tenant-scoped (RLS). The 7-stage pipeline matches a travel sales funnel.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantScoped, TimestampMixin, UUIDPrimaryKey

LEAD_STAGES = (
    "new",
    "contacted",
    "interested",
    "proposal",
    "negotiation",
    "won",
    "lost",
)
LEAD_SOURCES = ("meta", "web", "whatsapp", "instagram", "manual")
MESSAGE_CHANNELS = ("email", "sms", "whatsapp")
MESSAGE_DIRECTIONS = ("outbound", "inbound")
MESSAGE_STATUSES = ("draft", "queued", "sent", "delivered", "failed", "received")


class Lead(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "leads"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="new", index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    trip_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    activities: Mapped[list["LeadActivity"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="LeadActivity.created_at.desc()"
    )


class LeadActivity(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "lead_activities"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    lead_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    lead: Mapped["Lead"] = relationship(back_populates="activities")


class Message(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "messages"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    lead_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(10), nullable=False, default="email")
    direction: Mapped[str] = mapped_column(String(10), nullable=False, default="outbound")
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="draft")
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    lead: Mapped["Lead"] = relationship(back_populates="messages")


class MessageTemplate(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "message_templates"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    channel: Mapped[str] = mapped_column(String(10), nullable=False, default="email")
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Position in the default follow-up sequence (0 = first touch).
    step: Mapped[int] = mapped_column(Integer, default=0)


class ScheduledFollowup(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "scheduled_followups"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    lead_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(10), nullable=False, default="email")
    step: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="scheduled")
