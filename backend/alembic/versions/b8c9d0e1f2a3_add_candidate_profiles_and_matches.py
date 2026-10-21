"""add candidate profiles and match assessments

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("experience_summary", sa.Text(), nullable=True),
        sa.Column("target_roles", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("preferred_locations", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("remote_preference", sa.String(length=20), nullable=True),
        sa.Column("resume_version", sa.String(length=255), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "job_match_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_revision", sa.Integer(), nullable=False),
        sa.Column("opportunity_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scoring_model_version", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("evidence_coverage", sa.Numeric(5, 4), nullable=False),
        sa.Column("matched_skills", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("unverified_requirements", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("explanations", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("eligibility_status", sa.String(length=30), nullable=False),
        sa.Column("ranking_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["job_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id", "candidate_profile_id", "profile_revision", name="job_match_assessment_revision_unique"),
    )
    op.create_index("ix_job_match_assessments_opportunity_id", "job_match_assessments", ["opportunity_id"])


def downgrade() -> None:
    op.drop_index("ix_job_match_assessments_opportunity_id", table_name="job_match_assessments")
    op.drop_table("job_match_assessments")
    op.drop_table("candidate_profiles")