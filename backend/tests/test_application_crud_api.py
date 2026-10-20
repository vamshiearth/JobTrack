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
    user_a = User(email=f"{uuid.uuid4()}@example.com", display_name="User A")
    user_b = User(email=f"{uuid.uuid4()}@example.com", display_name="User B")
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
        json={"company_name": "Example Co", "job_title": "Developer", "notes": "Initial"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_get_application_detail(context):
    db, user_a, _, client = context
    application_id = create_application(client, user_a.id)

    response = client.get(f"/api/v1/applications/{application_id}")

    assert response.status_code == 200
    assert response.json()["id"] == application_id


def test_get_other_users_application_returns_404(context):
    _, user_a, user_b, client = context
    application_id = create_application(client, user_a.id)
    app.dependency_overrides[get_current_user_id] = lambda: user_b.id

    response = client.get(f"/api/v1/applications/{application_id}")

    assert response.status_code == 404


def test_patch_updates_allowed_fields(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)

    response = client.patch(
        f"/api/v1/applications/{application_id}",
        json={"job_title": "Senior Developer", "notes": None},
    )

    assert response.status_code == 200
    assert response.json()["job_title"] == "Senior Developer"
    assert response.json()["notes"] is None


def test_patch_cannot_change_progress_or_ownership(context):
    _, user_a, _, client = context
    application_id = create_application(client, user_a.id)

    response = client.patch(
        f"/api/v1/applications/{application_id}",
        json={"current_stage": "REJECTED", "user_id": str(user_a.id)},
    )

    assert response.status_code == 422


def test_other_user_cannot_patch_application(context):
    _, user_a, user_b, client = context
    application_id = create_application(client, user_a.id)
    app.dependency_overrides[get_current_user_id] = lambda: user_b.id

    response = client.patch(
        f"/api/v1/applications/{application_id}",
        json={"notes": "Stolen update"},
    )

    assert response.status_code == 404


def test_delete_application_removes_timeline(context):
    db, user_a, _, client = context
    application_id = create_application(client, user_a.id)
    event_id = db.scalar(
        select(ApplicationEvent.id).where(
            ApplicationEvent.job_application_id == uuid.UUID(application_id)
        )
    )

    response = client.delete(f"/api/v1/applications/{application_id}")

    assert response.status_code == 204
    assert db.get(JobApplication, uuid.UUID(application_id)) is None
    assert db.get(ApplicationEvent, event_id) is None


def test_other_user_cannot_delete_application(context):
    _, user_a, user_b, client = context
    application_id = create_application(client, user_a.id)
    app.dependency_overrides[get_current_user_id] = lambda: user_b.id

    response = client.delete(f"/api/v1/applications/{application_id}")

    assert response.status_code == 404


def test_missing_application_returns_404(context):
    _, user_a, _, client = context
    app.dependency_overrides[get_current_user_id] = lambda: user_a.id

    response = client.get(f"/api/v1/applications/{uuid.uuid4()}")

    assert response.status_code == 404


def test_invalid_application_id_returns_422(context):
    _, user_a, _, client = context
    app.dependency_overrides[get_current_user_id] = lambda: user_a.id

    response = client.get("/api/v1/applications/not-a-uuid")

    assert response.status_code == 422