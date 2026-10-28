"""Tenant (travel agency workspace) and User models.

``tenants`` and ``users`` are global registry tables (no RLS): users are looked
up by email at login before any tenant context exists. Tenant scoping for these
is enforced at the application layer.
"""
import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class UserRole(str, enum.Enum):
    owner = "owner"
    member = "member"


class Tenant(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    # Light onboarding state so the UI can resume where the user left off.
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    # When true, the followup agent sends first-touch/sequence messages
    # automatically; otherwise they wait in the Approval Center (HITL).
    auto_followup: Mapped[bool] = mapped_column(Boolean, default=False)

    users: Mapped[list["User"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class User(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.owner, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Embedded in every JWT; bumping it (logout) revokes all of the user's
    # outstanding access + refresh tokens.
    token_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="users")
