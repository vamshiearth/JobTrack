import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import EmailMessage, GmailConnection, JobApplication, ReviewItem, User
from app.services.gmail_oauth import GMAIL_METADATA_SCOPE
from app.services.recruitment_classification_service import ClassificationNotEligible, classify_saved_messages


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


def seed(db: Session, *, status="CONNECTED"):
    user = User(email=f"intel-{uuid.uuid4()}@example.com", display_name="Intel")
    db.add(user)
    db.flush()
    connection = GmailConnection(user_id=user.id, google_subject=str(uuid.uuid4()), email_address=user.email, granted_scopes=[GMAIL_METADATA_SCOPE], connection_status=status)
    db.add(connection)
    db.flush()
    message = EmailMessage(gmail_connection_id=connection.id, gmail_message_id=str(uuid.uuid4()), gmail_thread_id=str(uuid.uuid4()), received_at=datetime.now(timezone.utc), sender_address="recruiting@acme.com", subject="Acme interview invitation", classification_kind="UNKNOWN", processing_status="PENDING")
    db.add(message)
    db.flush()
    return user, connection, message


def test_classification_creates_one_pending_review_and_is_idempotent(db):
    user, connection, message = seed(db)
    first = classify_saved_messages(db, user_id=user.id, connection_id=connection.id)
    second = classify_saved_messages(db, user_id=user.id, connection_id=connection.id)
    reviews = db.scalars(select(ReviewItem).where(ReviewItem.email_message_id == message.id)).all()
    assert first.proposed == 1
    assert second.proposed == 0
    assert len(reviews) == 1
    assert message.classification_kind == "INTERVIEW_INVITATION"


def test_disconnected_connection_is_rejected(db):
    user, connection, _ = seed(db, status="DISCONNECTED")
    with pytest.raises(ClassificationNotEligible):
        classify_saved_messages(db, user_id=user.id, connection_id=connection.id)


def test_unmatched_message_creates_review_without_application_change(db):
    user, connection, message = seed(db)
    application = JobApplication(user_id=user.id, company_name="Other Employer", job_title="Designer", application_source="MANUAL", current_stage="APPLIED", next_action_owner="EMPLOYER", last_activity_at=datetime.now(timezone.utc))
    db.add(application)
    db.flush()
    before_stage = application.current_stage
    result = classify_saved_messages(db, user_id=user.id, connection_id=connection.id)
    review = db.scalar(select(ReviewItem).where(ReviewItem.email_message_id == message.id))
    assert result.proposed == 1
    assert review is not None
    assert review.suggested_application_id is None
    assert application.current_stage == before_stage


def test_classification_candidates_are_scoped_to_authenticated_user(db):
    user, connection, message = seed(db)
    own_application = JobApplication(user_id=user.id, company_name="Acme Robotics", job_title="Backend Engineer", application_source="MANUAL", current_stage="APPLIED", next_action_owner="EMPLOYER", last_activity_at=datetime.now(timezone.utc))
    other_user = User(email=f"other-{uuid.uuid4()}@example.com", display_name="Other")
    db.add(other_user)
    db.flush()
    other_application = JobApplication(user_id=other_user.id, company_name="Acme Robotics", job_title="Senior Platform Engineer", application_source="MANUAL", current_stage="APPLIED", next_action_owner="EMPLOYER", last_activity_at=datetime.now(timezone.utc))
    db.add_all([own_application, other_application])
    message.subject = "Acme Robotics Senior Platform Engineer interview invitation"
    db.flush()

    classify_saved_messages(db, user_id=user.id, connection_id=connection.id)

    review = db.scalar(select(ReviewItem).where(ReviewItem.email_message_id == message.id))
    assert review is not None
    assert review.suggested_application_id == own_application.id
    assert review.suggested_application_id != other_application.id
