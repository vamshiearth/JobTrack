"""add application preparation packages

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_preparations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_assessment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_fingerprint", sa.String(length=255), nullable=False),
        sa.Column("draft_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resume_suggestions", postgresql.JSONB(), nullable=False),
        sa.Column("application_answers", postgresql.JSONB(), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_revision", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT', 'NEEDS_REVIEW', 'APPROVED', 'STALE', 'ARCHIVED')", name="application_preparation_status_valid"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["job_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_assessment_id"], ["job_match_assessments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_application_preparations_user_id", "application_preparations", ["user_id"])
    op.create_index("ix_application_preparations_opportunity_id", "application_preparations", ["opportunity_id"])


def downgrade() -> None:
    op.drop_index("ix_application_preparations_opportunity_id", table_name="application_preparations")
    op.drop_index("ix_application_preparations_user_id", table_name="application_preparations")
    op.drop_table("application_preparations")
