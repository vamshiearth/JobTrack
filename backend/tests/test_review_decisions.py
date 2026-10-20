import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine, get_db
from app.dependencies.auth import get_auth_context
from app.main import app
from app.models import ApplicationEvent, EmailMessage, GmailConnection, JobApplication, ReviewItem, User
from app.services.auth_session_service import csrf_for_session, issue_session
from app.services.review_decisions import ReviewConflict, approve_review

ORIGIN = "http://localhost:5173"


@pytest.fixture
def context():
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    app.dependency_overrides[get_db] = lambda: (yield db)
    try:
        yield db
    finally:
        app.dependency_overrides.clear()
        db.close()
        transaction.rollback()
        connection.close()


def user(db: Session, label: str) -> User:
    value = User(email=f"{label}-{uuid.uuid4()}@example.com")
    db.add(value)
    db.flush()
    return value


def review_fixture(db: Session, owner: User, *, event_kind: str | None = "RECRUITER_CONTACTED"):
    connection = GmailConnection(
        user_id=owner.id,
        google_subject=f"google-{uuid.uuid4()}",
        email_address=owner.email,
        granted_scopes=["https://www.googleapis.com/auth/gmail.metadata"],
        connection_status="CONNECTED",
    )
    application = JobApplication(
        user_id=owner.id,
        company_name="Example Co",
        job_title="Developer",
        application_source="MANUAL",
        current_stage="APPLIED",
        next_action_owner="USER",
        last_activity_at=datetime.now(timezone.utc),
    )
    message = EmailMessage(
        gmail_connection=connection,
        gmail_message_id=str(uuid.uuid4()),
        gmail_thread_id=str(uuid.uuid4()),
        sender_address="careers@example.com",
        subject="Recruitment update",
        received_at=datetime.now(timezone.utc),
        classification_kind="RECRUITMENT_SIGNAL",
        processing_status="CLASSIFIED",
    )
    review = ReviewItem(
        user_id=owner.id,
        email_message=message,
        suggested_application_id=application.id,
        suggested_event_kind=event_kind,
        confidence="0.900",
        reason="subject signal; sender signal",
        review_status="PENDING",
    )
    db.add_all([connection, application, message, review])
    db.flush()
    return application, review


def authenticated_client(db: Session, owner: User):
    token = issue_session(db, user=owner, lifetime_days=7)
    db.flush()
    client = TestClient(app)
    client.cookies.set(get_settings().auth_cookie_name, token, path="/api/v1")
    return client, csrf_for_session(token)


def events_for(db: Session, application_id):
    return list(db.scalars(select(ApplicationEvent).where(ApplicationEvent.job_application_id == application_id)).all())


def test_valid_approval_creates_one_event_and_is_idempotent(context):
    owner = user(context, "owner")
    application, review = review_fixture(context, owner)
    client, csrf = authenticated_client(context, owner)

    first = client.post(
        f"/api/v1/review-items/{review.id}/approve",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={"application_id": str(application.id)},
    )
    second = client.post(
        f"/api/v1/review-items/{review.id}/approve",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={"application_id": str(application.id)},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["created_event_id"] == first.json()["created_event_id"]
    assert len(events_for(context, application.id)) == 1
    assert context.get(ReviewItem, review.id).review_status == "APPROVED"


def test_conflicting_approval_and_rejection_state(context):
    owner = user(context, "owner")
    application, review = review_fixture(context, owner)
    client, csrf = authenticated_client(context, owner)
    headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}

    approved = client.post(f"/api/v1/review-items/{review.id}/approve", headers=headers, json={"application_id": str(application.id)})
    conflicting = client.post(f"/api/v1/review-items/{review.id}/approve", headers=headers, json={"application_id": str(uuid.uuid4())})
    rejected = client.post(f"/api/v1/review-items/{review.id}/reject", headers=headers)

    assert approved.status_code == 200
    assert conflicting.status_code == 409
    assert rejected.status_code == 409
    assert len(events_for(context, application.id)) == 1


def test_rejection_creates_no_event_and_cannot_be_approved(context):
    owner = user(context, "owner")
    application, review = review_fixture(context, owner)
    client, csrf = authenticated_client(context, owner)
    headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}

    rejected = client.post(f"/api/v1/review-items/{review.id}/reject", headers=headers)
    approved = client.post(f"/api/v1/review-items/{review.id}/approve", headers=headers, json={"application_id": str(application.id)})

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    assert approved.status_code == 409
    assert events_for(context, application.id) == []
    assert context.get(ReviewItem, review.id).review_status == "DISMISSED"


def test_review_and_application_are_owner_scoped(context):
    owner = user(context, "owner")
    other = user(context, "other")
    application, review = review_fixture(context, owner)
    client, csrf = authenticated_client(context, other)

    detail = client.get(f"/api/v1/review-items/{review.id}")
    approve = client.post(
        f"/api/v1/review-items/{review.id}/approve",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={"application_id": str(application.id)},
    )

    assert detail.status_code == 404
    assert approve.status_code == 404
    assert events_for(context, application.id) == []


def test_approval_requires_csrf_and_trusted_origin(context):
    owner = user(context, "owner")
    application, review = review_fixture(context, owner)
    client, csrf = authenticated_client(context, owner)

    missing = client.post(f"/api/v1/review-items/{review.id}/approve", json={"application_id": str(application.id)})
    untrusted = client.post(
        f"/api/v1/review-items/{review.id}/approve",
        headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf},
        json={"application_id": str(application.id)},
    )

    assert missing.status_code == 403
    assert untrusted.status_code == 403
    assert context.get(ReviewItem, review.id).review_status == "PENDING"


def test_missing_interview_round_rolls_back_and_leaves_review_pending(context):
    owner = user(context, "owner")
    application, review = review_fixture(context, owner, event_kind="INTERVIEW_SCHEDULED")
    with pytest.raises(ReviewConflict):
        approve_review(context, review_id=review.id, user_id=owner.id, application_id=application.id, interview_round=None)
    context.expire_all()
    assert context.get(ReviewItem, review.id).review_status == "PENDING"
    assert events_for(context, application.id) == []


def test_service_exception_rolls_back_event_and_review(context, monkeypatch):
    owner = user(context, "owner")
    application, review = review_fixture(context, owner)

    from app.services import review_decisions

    def fail_event(*args, **kwargs):
        context.add(ApplicationEvent(job_application_id=application.id, event_kind="RECRUITER_CONTACTED", origin="MANUAL", verified_by_user=True, idempotency_key="injected", occurred_at=datetime.now(timezone.utc)))
        context.flush()
        raise RuntimeError("injected database failure")

    monkeypatch.setattr(review_decisions, "record_application_event", fail_event)
    savepoint = context.begin_nested()
    with pytest.raises(RuntimeError):
        approve_review(context, review_id=review.id, user_id=owner.id, application_id=application.id, interview_round=None)
    savepoint.rollback()
    context.expire_all()

    assert context.get(ReviewItem, review.id).review_status == "PENDING"
    assert events_for(context, application.id) == []
