"""Audit log — the first tenant-scoped, RLS-protected table.

Serves the cross-cutting "who did/approved/sent what" requirement and acts as a
concrete table to verify tenant isolation end-to-end.
"""
import uuid
from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, TimestampMixin, UUIDPrimaryKey


class AuditLog(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "audit_log"

    tenant_id: Mapped[uuid.UUID] = TenantScoped.tenant_fk()
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
