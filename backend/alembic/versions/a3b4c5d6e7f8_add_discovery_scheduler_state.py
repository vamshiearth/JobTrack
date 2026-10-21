"""add discovery scheduler state

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
"""

from alembic import op
import sqlalchemy as sa

revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("discovery_sources", sa.Column("last_refresh_status", sa.String(length=20)))
    op.add_column("discovery_sources", sa.Column("next_refresh_at", sa.DateTime(timezone=True)))
    op.add_column("discovery_sources", sa.Column("lease_token", sa.String(length=64)))
    op.add_column("discovery_sources", sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
    op.create_unique_constraint("discovery_source_lease_token_unique", "discovery_sources", ["lease_token"])


def downgrade() -> None:
    op.drop_constraint("discovery_source_lease_token_unique", "discovery_sources", type_="unique")
    op.drop_column("discovery_sources", "lease_expires_at")
    op.drop_column("discovery_sources", "lease_token")
    op.drop_column("discovery_sources", "next_refresh_at")
    op.drop_column("discovery_sources", "last_refresh_status")