import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine, get_db
from app.main import app
from app.models import AuthSession, User
from app.services.auth_session_service import csrf_for_session, issue_session

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


def create_user(db: Session, label: str) -> User:
    user = User(email=f"{label}-{uuid.uuid4()}@example.com", display_name=label)
    db.add(user)
    db.flush()
    return user


def client_for(db: Session, user: User) -> tuple[TestClient, str]:
    token = issue_session(db, user=user, lifetime_days=7)
    db.flush()
    client = TestClient(app)
    client.cookies.set(get_settings().auth_cookie_name, token, path="/api/v1")
    return client, csrf_for_session(token)


def test_authenticated_application_lifecycle(context):
    owner = create_user(context, "owner")
    other_user = create_user(context, "other")
    owner_client, csrf_token = client_for(context, owner)
    other_client, _ = client_for(context, other_user)

    with owner_client, other_client:
        create_response = owner_client.post(
            "/api/v1/applications",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
            json={
                "company_name": "Example Technologies",
                "job_title": "Software Engineer",
                "notes": "Initial application",
            },
        )
        assert create_response.status_code == 201
        application_id = create_response.json()["id"]

        events_response = owner_client.get(
            f"/api/v1/applications/{application_id}/events"
        )
        assert events_response.status_code == 200
        assert any(
            event["event_kind"] == "APPLICATION_SUBMITTED"
            for event in events_response.json()["items"]
        )

        update_response = owner_client.patch(
            f"/api/v1/applications/{application_id}",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
            json={"job_title": "Updated Software Engineer"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["job_title"] == "Updated Software Engineer"

        event_response = owner_client.post(
            f"/api/v1/applications/{application_id}/events",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
            json={
                "event_kind": "RECRUITER_CONTACTED",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "client_request_id": str(uuid.uuid4()),
            },
        )
        assert event_response.status_code in (200, 201)
        assert event_response.json()["event_kind"] == "RECRUITER_CONTACTED"

        detail_response = owner_client.get(
            f"/api/v1/applications/{application_id}"
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["current_stage"] == "SCREENING"

        assert other_client.get(
            f"/api/v1/applications/{application_id}"
        ).status_code == 404

        delete_response = owner_client.delete(
            f"/api/v1/applications/{application_id}",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
        )
        assert delete_response.status_code == 204
        assert owner_client.get(
            f"/api/v1/applications/{application_id}"
        ).status_code == 404
        assert owner_client.get(
            f"/api/v1/applications/{application_id}/events"
        ).status_code == 404
