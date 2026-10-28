"""Trip / itinerary models (Module 1). All tenant-scoped (RLS)."""
import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantScoped, TimestampMixin, UUIDPrimaryKey

# Trip lifecycle: draft -> generating -> pending_review -> approved
TRIP_STATUSES = ("draft", "generating", "pending_review", "approved")


class Trip(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "trips"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    destination: Mapped[str] = mapped_column(String(160), nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    audience: Mapped[str | None] = mapped_column(String(120), nullable=True)
    season: Mapped[str | None] = mapped_column(String(60), nullable=True)
    budget_per_person: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)

    days_plan: Mapped[list["ItineraryDay"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="ItineraryDay.day_number",
    )
    costing: Mapped["TripCosting | None"] = relationship(
        back_populates="trip", cascade="all, delete-orphan", uselist=False
    )


class ItineraryDay(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "itinerary_days"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    trip_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    activities: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    stay: Mapped[str | None] = mapped_column(String(200), nullable=True)
    transport: Mapped[str | None] = mapped_column(String(200), nullable=True)

    trip: Mapped["Trip"] = relationship(back_populates="days_plan")


class TripCosting(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "trip_costing"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    trip_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    per_person: Mapped[int | None] = mapped_column(Integer, nullable=True)
    breakdown: Mapped[list[Any]] = mapped_column(JSONB, default=list)

    trip: Mapped["Trip"] = relationship(back_populates="costing")
