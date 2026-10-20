import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.dependencies.auth import get_current_user_id
from app.main import app
from app.models import ApplicationEvent, User
from app.services.application_service import list_applications


@pytest.fixture
def api_context():
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    user_a = User(email=f"{uuid.uuid4()}@example.com", display_name="Test User A")
    user_b = User(email=f"{uuid.uuid4()}@example.com", display_name="Test User B")
    db.add_all([user_a, user_b])
    db.flush()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield db, user_a, user_b
    finally:
        app.dependency_overrides.clear()
        db.close()
        transaction.rollback()
        connection.close()


def test_unauthenticated_list_is_rejected():
    response = TestClient(app).get("/api/v1/applications")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_unauthenticated_create_is_rejected():
    response = TestClient(app).post(
        "/api/v1/applications",
        json={"company_name": "Example", "job_title": "Developer"},
    )

    assert response.status_code == 401


def test_create_application_and_initial_event(api_context):
    db, user_a, _ = api_context
    app.dependency_overrides[get_current_user_id] = lambda: user_a.id

    response = TestClient(app).post(
        "/api/v1/applications",
        json={
            "company_name": "Example Technologies",
            "job_title": "Backend Engineer",
            "applied_at": "2026-10-20",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["company_name"] == "Example Technologies"
    assert body["current_stage"] == "APPLIED"
    assert body["user_id"] == str(user_a.id)
    event = db.query(ApplicationEvent).filter_by(job_application_id=body["id"]).one()
    assert event.event_kind == "APPLICATION_SUBMITTED"
    assert event.origin == "MANUAL"


def test_list_returns_only_authenticated_users_applications(api_context):
    db, user_a, user_b = api_context
    app.dependency_overrides[get_current_user_id] = lambda: user_a.id
    client = TestClient(app)
    client.post(
        "/api/v1/applications",
        json={"company_name": "User A Co", "job_title": "Developer"},
    )
    app.dependency_overrides[get_current_user_id] = lambda: user_b.id
    client.post(
        "/api/v1/applications",
        json={"company_name": "User B Co", "job_title": "Developer"},
    )
    app.dependency_overrides[get_current_user_id] = lambda: user_a.id

    response = client.get("/api/v1/applications")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["company_name"] == "User A Co"


def test_list_empty_for_user_without_applications(api_context):
    _, user_a, _ = api_context
    app.dependency_overrides[get_current_user_id] = lambda: user_a.id

    response = TestClient(app).get("/api/v1/applications")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_service_list_is_user_scoped(api_context):
    db, user_a, user_b = api_context
    app.dependency_overrides[get_current_user_id] = lambda: user_a.id
    response = TestClient(app).post(
        "/api/v1/applications",
        json={"company_name": "Private Co", "job_title": "Developer"},
    )

    assert response.status_code == 201
    assert len(list_applications(db, user_id=user_b.id)) == 0