import uuid

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
    user_a = User(email=f"{uuid.uuid4()}@example.com", display_name="Workflow User A")
    user_b = User(email=f"{uuid.uuid4()}@example.com", display_name="Workflow User B")
    db.add_all([user_a, user_b])
    db.flush()
    identity = {"id": user_a.id}
    app.dependency_overrides[get_db] = lambda: (yield db)
    app.dependency_overrides[get_current_user_id] = lambda: identity["id"]
    try:
        yield TestClient(app), db, identity, user_a, user_b
    finally:
        app.dependency_overrides.clear()
        db.close()
        transaction.rollback()
        connection.close()


def create_job(client):
    response = client.post(
        "/api/v1/applications",
        json={"company_name": "Workflow Co", "job_title": "Platform Engineer"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def record_event(client, job_id, event_kind, request_id=None, **extra):
    payload = {
        "event_kind": event_kind,
        "occurred_at": "2026-10-20T18:00:00Z",
        "client_request_id": str(request_id or uuid.uuid4()),
    }
    payload.update(extra)
    return client.post(f"/api/v1/applications/{job_id}/events", json=payload)


def test_complete_application_workflow(context):
    client, db, identity, user_a, user_b = context
    job_id = create_job(client)
    assert record_event(client, job_id, "RECRUITER_CONTACTED").status_code == 201
    assert record_event(client, job_id, "ASSESSMENT_INVITED").status_code == 201
    assert record_event(client, job_id, "ASSESSMENT_COMPLETED").status_code == 201
    assert record_event(client, job_id, "INTERVIEW_SCHEDULED", interview_round=1).status_code == 201
    assert record_event(client, job_id, "INTERVIEW_COMPLETED", interview_round=1).status_code == 201
    assert record_event(client, job_id, "OFFER_RECEIVED").status_code == 201

    application = client.get(f"/api/v1/applications/{job_id}")
    assert application.status_code == 200
    assert application.json()["current_stage"] == "OFFER"
    assert application.json()["next_action_owner"] == "USER"
    assert client.get("/api/v1/applications", params={"q": "Workflow"}).json()["total"] == 1

    assert client.delete(f"/api/v1/applications/{job_id}").status_code == 204
    assert db.scalar(select(JobApplication).where(JobApplication.id == job_id)) is None
    assert db.scalar(select(ApplicationEvent).where(ApplicationEvent.job_application_id == job_id)) is None


def test_cross_user_cannot_access_workflow(context):
    client, db, identity, user_a, user_b = context
    job_id = create_job(client)
    identity["id"] = user_b.id
    base = f"/api/v1/applications/{job_id}"
    assert client.get(base).status_code == 404
    assert client.patch(base, json={"notes": "Unauthorized edit"}).status_code == 404
    assert client.delete(base).status_code == 404
    assert client.get(f"{base}/events").status_code == 404
    assert record_event(client, job_id, "RECRUITER_CONTACTED").status_code == 404
    assert client.get("/api/v1/applications").json()["items"] == []
    identity["id"] = user_a.id
    assert client.get(base).status_code == 200


def test_duplicate_event_does_not_create_new_event(context):
    client, db, identity, user_a, user_b = context
    job_id = create_job(client)
    request_id = uuid.uuid4()
    first = record_event(client, job_id, "RECRUITER_CONTACTED", request_id=request_id)
    second = record_event(client, job_id, "RECRUITER_CONTACTED", request_id=request_id)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert client.get(f"/api/v1/applications/{job_id}/events").json()["total"] == 2


def test_idempotency_payload_conflict(context):
    client, db, identity, user_a, user_b = context
    job_id = create_job(client)
    request_id = uuid.uuid4()
    assert record_event(client, job_id, "RECRUITER_CONTACTED", request_id=request_id).status_code == 201
    conflict = record_event(
        client, job_id, "RECRUITER_CONTACTED", request_id=request_id, details={"channel": "phone"}
    )
    assert conflict.status_code == 409


def test_failed_prerequisite_does_not_advance_stage(context):
    client, db, identity, user_a, user_b = context
    job_id = create_job(client)
    response = record_event(client, job_id, "ASSESSMENT_COMPLETED")
    assert response.status_code == 409
    assert client.get(f"/api/v1/applications/{job_id}").json()["current_stage"] == "APPLIED"


def test_closed_application_rejects_later_events(context):
    client, db, identity, user_a, user_b = context
    job_id = create_job(client)
    assert record_event(client, job_id, "REJECTION_RECEIVED").status_code == 201
    response = record_event(client, job_id, "RECRUITER_CONTACTED")
    assert response.status_code == 409
    assert client.get(f"/api/v1/applications/{job_id}").json()["current_stage"] == "REJECTED"


def test_manual_event_cannot_impersonate_gmail_origin(context):
    client, db, identity, user_a, user_b = context
    job_id = create_job(client)
    response = record_event(client, job_id, "APPLICATION_SUBMITTED")
    assert response.status_code == 409


def test_all_application_operations_require_auth():
    job_id = uuid.uuid4()
    base = f"/api/v1/applications/{job_id}"
    with TestClient(app) as client:
        responses = [
            client.get("/api/v1/applications"),
            client.post("/api/v1/applications", json={"company_name": "Example", "job_title": "Developer"}),
            client.get(base),
            client.patch(base, json={"notes": "Unauthorized"}),
            client.delete(base),
            client.get(f"{base}/events"),
            client.post(
                f"{base}/events",
                json={
                    "event_kind": "RECRUITER_CONTACTED",
                    "occurred_at": "2026-10-20T18:00:00Z",
                    "client_request_id": str(uuid.uuid4()),
                },
            ),
        ]
    assert all(response.status_code == 401 for response in responses)
