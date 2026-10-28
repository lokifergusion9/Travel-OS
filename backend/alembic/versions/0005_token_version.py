"""Auth hardening: users.token_version for JWT revocation (logout).

Revision ID: 0005_token_version
Revises: 0004_phase3
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_token_version"
down_revision: Union[str, None] = "0004_phase3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
