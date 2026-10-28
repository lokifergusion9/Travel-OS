"""Phase 2: CRM — leads, activities, messages, templates, scheduled followups.

Revision ID: 0003_crm
Revises: 0002_phase1
Create Date: 2026-06-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_crm"
down_revision: Union[str, None] = "0002_phase1"
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
    op.add_column(
        "tenants",
        sa.Column("auto_followup", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "leads",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("stage", sa.String(20), nullable=False, server_default="new"),
        sa.Column("score", sa.Integer(), server_default="0"),
        sa.Column("trip_id", UUID, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
    )
    op.create_index("ix_leads_tenant_id", "leads", ["tenant_id"])
    op.create_index("ix_leads_stage", "leads", ["stage"])
    _enable_rls("leads")

    op.create_table(
        "lead_activities",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
    )
    op.create_index("ix_lead_activities_tenant_id", "lead_activities", ["tenant_id"])
    op.create_index("ix_lead_activities_lead_id", "lead_activities", ["lead_id"])
    _enable_rls("lead_activities")

    op.create_table(
        "messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False, server_default="email"),
        sa.Column("direction", sa.String(10), nullable=False, server_default="outbound"),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="draft"),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
    )
    op.create_index("ix_messages_tenant_id", "messages", ["tenant_id"])
    op.create_index("ix_messages_lead_id", "messages", ["lead_id"])
    _enable_rls("messages")

    op.create_table(
        "message_templates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False, server_default="email"),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("step", sa.Integer(), server_default="0"),
        *_ts(),
    )
    op.create_index("ix_message_templates_tenant_id", "message_templates", ["tenant_id"])
    _enable_rls("message_templates")

    op.create_table(
        "scheduled_followups",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False, server_default="email"),
        sa.Column("step", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(12), nullable=False, server_default="scheduled"),
        *_ts(),
    )
    op.create_index("ix_scheduled_followups_tenant_id", "scheduled_followups", ["tenant_id"])
    op.create_index("ix_scheduled_followups_run_at", "scheduled_followups", ["run_at"])
    # NOTE: no RLS here — the background scheduler scans due rows across all
    # tenants, then binds the tenant GUC per row to write the (RLS) message.
    # Not exposed through any tenant-facing API.


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON message_templates")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON messages")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON lead_activities")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON leads")
    for table in ("scheduled_followups", "message_templates", "messages", "lead_activities", "leads"):
        op.drop_table(table)
    op.drop_column("tenants", "auto_followup")
