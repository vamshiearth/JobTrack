"""create user-owned job opportunities

Revision ID: a7b8c9d0e1f2
Revises: 4587f63b01bb
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a7b8c9d0e1f2"
down_revision = "4587f63b01bb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_job_id", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("job_title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("work_arrangement", sa.String(length=30), nullable=True),
        sa.Column("employment_type", sa.String(length=30), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('SAVED', 'ARCHIVED')", name="job_opportunity_status_valid"),
        sa.CheckConstraint("source_type = 'MANUAL'", name="job_opportunity_source_type_valid"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "normalized_url", name="job_opportunity_user_url_unique"),
    )
    op.create_index("ix_job_opportunities_user_id", "job_opportunities", ["user_id"])
    op.create_index("ix_job_opportunities_user_status", "job_opportunities", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_job_opportunities_user_status", table_name="job_opportunities")
    op.drop_index("ix_job_opportunities_user_id", table_name="job_opportunities")
    op.drop_table("job_opportunities")
