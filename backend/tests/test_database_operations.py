import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import (
    ApplicationEvent,
    EmailMessage,
    GmailConnection,
    JobApplication,
    ReviewItem,
    User,
)


@pytest.fixture
def db():
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


def create_user(db: Session) -> User:
    user = User(email=f"test-{uuid.uuid4()}@example.com", display_name="Test User")
    db.add(user)
    db.flush()
    return user


def create_application(db: Session, user: User) -> JobApplication:
    application = JobApplication(
        user_id=user.id,
        company_name="Example Technologies",
        job_title="Backend Software Engineer",
        applied_at=date.today(),
        application_source="MANUAL",
        current_stage="APPLIED",
        next_action_owner="EMPLOYER",
        last_activity_at=datetime.now(timezone.utc),
    )
    db.add(application)
    db.flush()
    return application


def create_gmail_connection(db: Session, user: User) -> GmailConnection:
    gmail = GmailConnection(
        user_id=user.id,
        google_subject=f"google-{uuid.uuid4()}",
        email_address=f"gmail-{uuid.uuid4()}@example.com",
        granted_scopes=["gmail.readonly"],
        connection_status="CONNECTED",
    )
    db.add(gmail)
    db.flush()
    return gmail


def create_email(
    db: Session,
    gmail: GmailConnection,
    application: JobApplication | None = None,
) -> EmailMessage:
    message = EmailMessage(
        gmail_connection_id=gmail.id,
        gmail_message_id=f"message-{uuid.uuid4()}",
        gmail_thread_id=f"thread-{uuid.uuid4()}",
        job_application_id=application.id if application else None,
        received_at=datetime.now(timezone.utc),
        classification_kind="UNKNOWN",
        processing_status="PENDING",
    )
    db.add(message)
    db.flush()
    return message


def test_create_and_read_application(db: Session):
    user = create_user(db)
    application = create_application(db, user)

    result = db.get(JobApplication, application.id)

    assert result is not None
    assert result.company_name == "Example Technologies"
    assert result.job_title == "Backend Software Engineer"
    assert result.user_id == user.id
    assert result.current_stage == "APPLIED"


def test_application_event_timeline(db: Session):
    user = create_user(db)
    application = create_application(db, user)
    event = ApplicationEvent(
        job_application_id=application.id,
        event_kind="ASSESSMENT_INVITED",
        origin="GMAIL",
        verified_by_user=False,
        idempotency_key=f"test-{uuid.uuid4()}",
        occurred_at=datetime.now(timezone.utc),
        details={"status": "INVITED"},
    )
    db.add(event)
    db.flush()

    events = db.scalars(
        select(ApplicationEvent).where(ApplicationEvent.job_application_id == application.id)
    ).all()

    assert len(events) == 1
    assert events[0].event_kind == "ASSESSMENT_INVITED"
    assert events[0].verified_by_user is False


def test_duplicate_gmail_message_rejected(db: Session):
    user = create_user(db)
    gmail = create_gmail_connection(db, user)
    first = create_email(db, gmail)
    duplicate = EmailMessage(
        gmail_connection_id=gmail.id,
        gmail_message_id=first.gmail_message_id,
        gmail_thread_id=first.gmail_thread_id,
        received_at=datetime.now(timezone.utc),
        classification_kind="UNKNOWN",
        processing_status="PENDING",
    )

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(duplicate)
            db.flush()


def test_invalid_application_stage_rejected(db: Session):
    user = create_user(db)

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(
                JobApplication(
                    user_id=user.id,
                    company_name="Invalid Example",
                    job_title="Software Engineer",
                    application_source="MANUAL",
                    current_stage="NOT_A_REAL_STAGE",
                    next_action_owner="EMPLOYER",
                    last_activity_at=datetime.now(timezone.utc),
                )
            )
            db.flush()


def test_invalid_user_foreign_key_rejected(db: Session):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(
                JobApplication(
                    user_id=uuid.uuid4(),
                    company_name="Foreign Key Test",
                    job_title="Developer",
                    application_source="MANUAL",
                    current_stage="APPLIED",
                    next_action_owner="EMPLOYER",
                    last_activity_at=datetime.now(timezone.utc),
                )
            )
            db.flush()


def test_invalid_review_confidence_rejected(db: Session):
    user = create_user(db)
    gmail = create_gmail_connection(db, user)
    email = create_email(db, gmail)

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(
                ReviewItem(
                    user_id=user.id,
                    email_message_id=email.id,
                    confidence=1.001,
                    reason="Invalid confidence",
                    review_status="PENDING",
                )
            )
            db.flush()


def test_application_deletion_behavior(db: Session):
    user = create_user(db)
    application = create_application(db, user)
    gmail = create_gmail_connection(db, user)
    email = create_email(db, gmail, application)
    event = ApplicationEvent(
        job_application_id=application.id,
        source_email_message_id=email.id,
        event_kind="APPLICATION_SUBMITTED",
        origin="GMAIL",
        idempotency_key=f"test-{uuid.uuid4()}",
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.flush()
    application_id = application.id
    email_id = email.id
    event_id = event.id

    db.delete(application)
    db.flush()
    db.expire_all()

    assert db.get(JobApplication, application_id) is None
    assert db.get(ApplicationEvent, event_id) is None
    retained_email = db.get(EmailMessage, email_id)
    assert retained_email is not None
    assert retained_email.job_application_id is None


def test_session_commit_stays_inside_outer_transaction(db: Session):
    user = create_user(db)
    application = create_application(db, user)
    application_id = application.id

    db.commit()
    result = db.get(JobApplication, application_id)

    assert result is not None
    assert result.company_name == "Example Technologies"
