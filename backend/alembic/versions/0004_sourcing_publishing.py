"""Phase 3: sourcing (vendors, deals) + publishing (social_accounts, scheduled_posts).

Revision ID: 0004_phase3
Revises: 0003_crm
Create Date: 2026-06-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_phase3"
down_revision: Union[str, None] = "0003_crm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def _ts():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def _enable_rls(table: str) -> None:
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
        "vendors",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="hotel"),
        sa.Column("location", sa.String(160), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_ts(),
    )
    op.create_index("ix_vendors_tenant_id", "vendors", ["tenant_id"])
    _enable_rls("vendors")

    op.create_table(
        "deals",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trip_id", UUID, sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=True),
        sa.Column("vendor_id", UUID, sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="hotel"),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("outreach_subject", sa.String(255), nullable=True),
        sa.Column("outreach_body", sa.Text(), nullable=True),
        sa.Column("sent", sa.Boolean(), server_default=sa.false()),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(8), server_default="INR"),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
    )
    op.create_index("ix_deals_tenant_id", "deals", ["tenant_id"])
    op.create_index("ix_deals_trip_id", "deals", ["trip_id"])
    op.create_index("ix_deals_vendor_id", "deals", ["vendor_id"])
    _enable_rls("deals")

    op.create_table(
        "social_accounts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False, server_default="instagram"),
        sa.Column("account_name", sa.String(160), nullable=False),
        sa.Column("ig_user_id", sa.String(80), nullable=True),
        sa.Column("access_token_enc", sa.Text(), nullable=True),
        sa.Column("connected", sa.Boolean(), server_default=sa.true()),
        sa.Column("is_dev", sa.Boolean(), server_default=sa.false()),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
    )
    op.create_index("ix_social_accounts_tenant_id", "social_accounts", ["tenant_id"])
    _enable_rls("social_accounts")

    op.create_table(
        "scheduled_posts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("social_account_id", UUID, sa.ForeignKey("social_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("trip_id", UUID, nullable=True),
        sa.Column("creative_asset_id", UUID, nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="scheduled"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
    )
    op.create_index("ix_scheduled_posts_tenant_id", "scheduled_posts", ["tenant_id"])
    op.create_index("ix_scheduled_posts_status", "scheduled_posts", ["status"])
    op.create_index("ix_scheduled_posts_scheduled_at", "scheduled_posts", ["scheduled_at"])
    _enable_rls("scheduled_posts")


def downgrade() -> None:
    for table in ("scheduled_posts", "social_accounts", "deals", "vendors"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.drop_table(table)
