"""add discovery work arrangement metadata

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""

from alembic import op
import sqlalchemy as sa

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("discovered_jobs", sa.Column("work_arrangement", sa.String(length=30)))
    op.add_column("discovered_jobs", sa.Column("location_restrictions", sa.Text()))


def downgrade() -> None:
    op.drop_column("discovered_jobs", "location_restrictions")
    op.drop_column("discovered_jobs", "work_arrangement")