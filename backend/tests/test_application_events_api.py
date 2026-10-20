import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.dependencies.auth import get_current_user_id
from app.main import app
from app.models import ApplicationEvent, JobApplication, User


@pytest.fixture
def context():
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    user_a = User(email=f"{uuid.uuid4()}@example.com")
    user_b = User(email=f"{uuid.uuid4()}@example.com")
    db.add_all([user_a, user_b])
    db.flush()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield db, user_a, user_b, TestClient(app)
    finally:
        app.dependency_overrides.clear()
        db.close()
        transaction.rollback()
        connection.close()


def create_application(client, user_id):
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    response = client.post(
        "/api/v1/applications",
        json={"company_name": "Example Co", "job_title": "Developer"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def event_payload(kind, request_id=None, **extra):
    payload = {
        "event_kind": kind,
        "occurred_at": "2026-10-20T18:00:00Z",
        "client_request_id": str(request_id or uuid.uuid4()),
    }
    payload.update(extra)
    return payload


def test_list_events_for_owned_application(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)

    response = client.get(f"/api/v1/applications/{application_id}/events")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["event_kind"] == "APPLICATION_SUBMITTED"


def test_record_assessment_invitation_updates_status(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)

    response = client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("ASSESSMENT_INVITED"),
    )

    assert response.status_code == 201
    detail = client.get(f"/api/v1/applications/{application_id}").json()
    assert detail["current_stage"] == "ASSESSMENT"
    assert detail["next_action_owner"] == "USER"


def test_assessment_completion_requires_invitation(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)

    response = client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("ASSESSMENT_COMPLETED"),
    )

    assert response.status_code == 409


def test_assessment_completion_updates_employer_action(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)
    client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("ASSESSMENT_INVITED"),
    )

    response = client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("ASSESSMENT_COMPLETED"),
    )

    assert response.status_code == 201
    detail = client.get(f"/api/v1/applications/{application_id}").json()
    assert detail["current_stage"] == "ASSESSMENT"
    assert detail["next_action_owner"] == "EMPLOYER"


def test_interview_events_require_round_and_prerequisite(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)
    invalid = client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("INTERVIEW_SCHEDULED"),
    )
    assert invalid.status_code == 422
    missing = client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("INTERVIEW_COMPLETED", interview_round=1),
    )
    assert missing.status_code == 409


def test_interview_round_is_tracked(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)
    client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("INTERVIEW_SCHEDULED", interview_round=1),
    )

    response = client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("INTERVIEW_COMPLETED", interview_round=1),
    )

    assert response.status_code == 201
    assert response.json()["interview_round"] == 1


def test_event_idempotency_returns_existing_event(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)
    request_id = uuid.uuid4()
    payload = event_payload("RECRUITER_CONTACTED", request_id)

    first = client.post(f"/api/v1/applications/{application_id}/events", json=payload)
    second = client.post(f"/api/v1/applications/{application_id}/events", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_event_idempotency_rejects_changed_payload(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)
    request_id = uuid.uuid4()
    first = client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("RECRUITER_CONTACTED", request_id, details={"channel": "email"}),
    )
    second = client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("RECRUITER_CONTACTED", request_id, details={"channel": "phone"}),
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_other_user_cannot_access_events(context):
    _, user_a, user_b, client = context
    application_id = create_application(client, user_a.id)
    app.dependency_overrides[get_current_user_id] = lambda: user_b.id

    response = client.get(f"/api/v1/applications/{application_id}/events")

    assert response.status_code == 404


def test_rejection_closes_application(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)
    response = client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("REJECTION_RECEIVED"),
    )

    assert response.status_code == 201
    assert client.get(f"/api/v1/applications/{application_id}").json()["current_stage"] == "REJECTED"


def test_closed_application_rejects_later_events(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)
    client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("REJECTION_RECEIVED"),
    )

    response = client.post(
        f"/api/v1/applications/{application_id}/events",
        json=event_payload("RECRUITER_CONTACTED"),
    )

    assert response.status_code == 409
