"""Phase 1: trips, itinerary_days, trip_costing, creative_assets, approvals.

Revision ID: 0002_phase1
Revises: 0001_initial
Create Date: 2026-06-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase1"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def _ts():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def _enable_rls(table: str) -> None:
    """Enable tenant isolation: rows filtered by the app.current_tenant GUC."""
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """
    )


def upgrade() -> None:
    op.create_table(
        "trips",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("destination", sa.String(160), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("audience", sa.String(120), nullable=True),
        sa.Column("season", sa.String(60), nullable=True),
        sa.Column("budget_per_person", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("overview", sa.Text(), nullable=True),
        *_ts(),
    )
    op.create_index("ix_trips_tenant_id", "trips", ["tenant_id"])
    _enable_rls("trips")

    op.create_table(
        "itinerary_days",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trip_id", UUID, sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("activities", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("stay", sa.String(200), nullable=True),
        sa.Column("transport", sa.String(200), nullable=True),
        *_ts(),
    )
    op.create_index("ix_itinerary_days_tenant_id", "itinerary_days", ["tenant_id"])
    op.create_index("ix_itinerary_days_trip_id", "itinerary_days", ["trip_id"])
    _enable_rls("itinerary_days")

    op.create_table(
        "trip_costing",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trip_id", UUID, sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("currency", sa.String(8), server_default="INR"),
        sa.Column("per_person", sa.Integer(), nullable=True),
        sa.Column("breakdown", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        *_ts(),
    )
    op.create_index("ix_trip_costing_tenant_id", "trip_costing", ["tenant_id"])
    _enable_rls("trip_costing")

    op.create_table(
        "creative_assets",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trip_id", UUID, sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending_review"),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
    )
    op.create_index("ix_creative_assets_tenant_id", "creative_assets", ["tenant_id"])
    op.create_index("ix_creative_assets_trip_id", "creative_assets", ["trip_id"])
    _enable_rls("creative_assets")

    op.create_table(
        "approvals",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", UUID, nullable=False),
        sa.Column("trip_id", UUID, nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("decided_by", UUID, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
    )
    op.create_index("ix_approvals_tenant_id", "approvals", ["tenant_id"])
    op.create_index("ix_approvals_status", "approvals", ["status"])
    _enable_rls("approvals")


def downgrade() -> None:
    for table in ("approvals", "creative_assets", "trip_costing", "itinerary_days", "trips"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.drop_table(table)
