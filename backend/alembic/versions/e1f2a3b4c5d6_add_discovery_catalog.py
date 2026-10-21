"""add persistent job discovery catalog

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discovery_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("board_token", sa.String(length=128), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("provider = 'GREENHOUSE'", name="discovery_provider_valid"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "board_token", name="discovery_source_provider_board_unique"),
    )
    op.create_table(
        "discovered_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_job_id", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("job_title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("availability_status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "availability_status IN ('ACTIVE', 'NOT_SEEN', 'UNKNOWN')",
            name="discovered_job_availability_valid",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["discovery_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "provider_job_id", name="discovered_job_source_provider_unique"),
    )
    op.create_index("ix_discovered_jobs_status", "discovered_jobs", ["availability_status"])


def downgrade() -> None:
    op.drop_index("ix_discovered_jobs_status", table_name="discovered_jobs")
    op.drop_table("discovered_jobs")
    op.drop_table("discovery_sources")
