"""add application handoffs and submission confirmations

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_handoffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preparation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_revision", sa.Integer(), nullable=False),
        sa.Column("source_url_snapshot", sa.Text(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["preparation_id"], ["application_preparations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_application_handoffs_user_id", "application_handoffs", ["user_id"])
    op.create_table(
        "application_submission_confirmations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preparation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("handoff_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confirmation_method", sa.String(length=30), nullable=False),
        sa.Column("employer_confirmation_reference", sa.String(length=255), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["preparation_id"], ["application_preparations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["handoff_id"], ["application_handoffs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_application_id"], ["job_applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("preparation_id", name="submission_confirmation_preparation_unique"),
        sa.UniqueConstraint("idempotency_key", name="submission_confirmation_idempotency_unique"),
    )
    op.create_index("ix_submission_confirmations_user_id", "application_submission_confirmations", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_submission_confirmations_user_id", table_name="application_submission_confirmations")
    op.drop_table("application_submission_confirmations")
    op.drop_index("ix_application_handoffs_user_id", table_name="application_handoffs")
    op.drop_table("application_handoffs")