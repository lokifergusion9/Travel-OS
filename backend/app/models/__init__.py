"""Import all models so Alembic autogenerate and metadata see them."""
from app.models.approval import Approval
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.creative import CreativeAsset
from app.models.lead import (
    Lead,
    LeadActivity,
    Message,
    MessageTemplate,
    ScheduledFollowup,
)
from app.models.publishing import ScheduledPost, SocialAccount
from app.models.sourcing import Deal, Vendor
from app.models.tenant import Tenant, User, UserRole
from app.models.trip import ItineraryDay, Trip, TripCosting

__all__ = [
    "Base",
    "Tenant",
    "User",
    "UserRole",
    "AuditLog",
    "Trip",
    "ItineraryDay",
    "TripCosting",
    "CreativeAsset",
    "Approval",
    "Lead",
    "LeadActivity",
    "Message",
    "MessageTemplate",
    "ScheduledFollowup",
    "Vendor",
    "Deal",
    "SocialAccount",
    "ScheduledPost",
]
