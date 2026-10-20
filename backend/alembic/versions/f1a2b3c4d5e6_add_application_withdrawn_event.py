"""allow application withdrawn timeline events

Revision ID: f1a2b3c4d5e6
Revises: d4d0b009600b
"""

from alembic import op


revision = "f1a2b3c4d5e6"
down_revision = "d4d0b009600b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_application_events_event_kind_valid"),
        "application_events",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_application_events_event_kind_valid"),
        "application_events",
        "event_kind IN ('APPLICATION_SUBMITTED', 'RECRUITER_CONTACTED', 'ASSESSMENT_INVITED', 'ASSESSMENT_COMPLETED', 'INTERVIEW_SCHEDULED', 'INTERVIEW_COMPLETED', 'OFFER_RECEIVED', 'REJECTION_RECEIVED', 'APPLICATION_WITHDRAWN', 'MANUAL_CORRECTION')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_application_events_event_kind_valid"),
        "application_events",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_application_events_event_kind_valid"),
        "application_events",
        "event_kind IN ('APPLICATION_SUBMITTED', 'RECRUITER_CONTACTED', 'ASSESSMENT_INVITED', 'ASSESSMENT_COMPLETED', 'INTERVIEW_SCHEDULED', 'INTERVIEW_COMPLETED', 'OFFER_RECEIVED', 'REJECTION_RECEIVED', 'MANUAL_CORRECTION')",
    )