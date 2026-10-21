"""Phase 10 controlled review approval coverage using rollback-isolated data."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import ApplicationEvent, EmailMessage, GmailConnection, JobApplication, ReviewItem, User
from app.schemas.application_event import EventKind
from app.services.event_rules import CLOSED_STAGES, get_status_for_event
from app.services.recruitment_classification_service import classify_saved_messages
from app.services.review_decisions import ReviewConflict, approve_review


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def synthetic_review(db: Session):
    owner = User(email=f"phase10-{uuid.uuid4()}@example.com")
    connection = GmailConnection(
        user=owner,
        google_subject=f"google-{uuid.uuid4()}",
        email_address=owner.email,
        granted_scopes=["https://www.googleapis.com/auth/gmail.metadata"],
        connection_status="CONNECTED",
    )
    application = JobApplication(
        user=owner,
        company_name="Example Robotics",
        job_title="Backend Engineer",
        application_source="MANUAL",
        current_stage="APPLIED",
        next_action_owner="EMPLOYER",
        last_activity_at=datetime.now(timezone.utc),
    )
    message = EmailMessage(
        gmail_connection=connection,
        gmail_message_id=str(uuid.uuid4()),
        gmail_thread_id=str(uuid.uuid4()),
        sender_address="recruiting@example-robotics.test",
        subject="Example Robotics recruiter outreach",
        received_at=datetime.now(timezone.utc),
        classification_kind="RECRUITER_CONTACT",
        processing_status="CLASSIFIED",
    )
    review = ReviewItem(
        user=owner,
        email_message=message,
        suggested_application=application,
        suggested_event_kind=EventKind.RECRUITER_CONTACTED.value,
        confidence="0.900",
        reason="controlled synthetic review",
        review_status="PENDING",
    )
    db.add(review)
    db.flush()
    return owner, connection, application, message, review


def events_for(db: Session, application_id):
    return list(db.scalars(select(ApplicationEvent).where(ApplicationEvent.job_application_id == application_id)).all())


def test_review_approval_end_to_end_creates_one_derived_event(db):
    owner, _, application, _, review = synthetic_review(db)
    expected_stage, expected_owner = get_status_for_event(EventKind.RECRUITER_CONTACTED)

    result = approve_review(
        db,
        review_id=review.id,
        user_id=owner.id,
        application_id=application.id,
        interview_round=None,
    )
    db.commit()
    db.expire_all()

    saved_review = db.get(ReviewItem, review.id)
    refreshed_application = db.get(JobApplication, application.id)
    events = events_for(db, application.id)
    assert result.status == "APPROVED"
    assert saved_review.review_status == "APPROVED"
    assert saved_review.suggested_application_id == application.id
    assert result.created_event_id == events[0].id
    assert len(events) == 1
    assert events[0].event_kind == EventKind.RECRUITER_CONTACTED.value
    assert events[0].job_application_id == application.id
    assert events[0].origin == "MANUAL"
    assert events[0].verified_by_user is True
    assert refreshed_application.current_stage == expected_stage
    assert refreshed_application.next_action_owner == expected_owner


def test_repeat_approval_is_idempotent_and_conflicting_selection_is_rejected(db):
    owner, _, application, _, review = synthetic_review(db)
    first = approve_review(db, review_id=review.id, user_id=owner.id, application_id=application.id, interview_round=None)
    second = approve_review(db, review_id=review.id, user_id=owner.id, application_id=application.id, interview_round=None)
    assert second.created_event_id == first.created_event_id
    assert len(events_for(db, application.id)) == 1
    with pytest.raises(ReviewConflict):
        approve_review(db, review_id=review.id, user_id=owner.id, application_id=uuid.uuid4(), interview_round=None)


def test_closed_application_rejects_approval_without_event(db):
    owner, _, application, _, review = synthetic_review(db)
    application.current_stage = next(iter(CLOSED_STAGES))
    db.flush()

    savepoint = db.begin_nested()
    with pytest.raises(ReviewConflict):
        approve_review(db, review_id=review.id, user_id=owner.id, application_id=application.id, interview_round=None)
    savepoint.rollback()
    db.expire_all()

    assert db.get(ReviewItem, review.id).review_status == "PENDING"
    assert events_for(db, application.id) == []


def test_rejected_review_stays_closed_when_classification_repeats(db):
    owner, connection, _, message, review = synthetic_review(db)
    review.review_status = "DISMISSED"
    db.flush()

    result = classify_saved_messages(db, user_id=owner.id, connection_id=connection.id)
    reviews = list(db.scalars(select(ReviewItem).where(ReviewItem.email_message_id == message.id)).all())

    assert result.proposed == 0
    assert result.skipped == 1
    assert len(reviews) == 1
    assert reviews[0].review_status == "DISMISSED"
    assert events_for(db, review.suggested_application_id) == []
