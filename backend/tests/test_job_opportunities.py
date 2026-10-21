import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.dependencies.auth import get_current_user_id
from app.main import app
from app.models import ApplicationEvent, JobApplication, JobOpportunity, User


@pytest.fixture
def api_context():
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    user_a = User(email=f"opportunity-a-{uuid.uuid4()}@example.com")
    user_b = User(email=f"opportunity-b-{uuid.uuid4()}@example.com")
    db.add_all([user_a, user_b])
    db.flush()
    app.dependency_overrides[get_db] = lambda: (yield db)
    try:
        yield db, user_a, user_b
    finally:
        app.dependency_overrides.clear()
        db.close()
        transaction.rollback()
        connection.close()


def client_for(user):
    app.dependency_overrides[get_current_user_id] = lambda: user.id
    return TestClient(app)


def payload(url="https://careers.example.com/jobs/12345"):
    return {
        "company_name": "Example Technologies",
        "job_title": "Junior Java Developer",
        "location": "Boston, MA",
        "work_arrangement": "HYBRID",
        "employment_type": "FULL_TIME",
        "description": "Illustrative development role.",
        "source_type": "MANUAL",
        "source_url": url,
    }


def test_valid_import_creates_opportunity_without_application_event(api_context):
    db, user_a, _ = api_context
    response = client_for(user_a).post("/api/v1/opportunities", json=payload())
    assert response.status_code == 201
    body = response.json()
    assert body["company_name"] == "Example Technologies"
    assert body["status"] == "SAVED"
    assert db.scalar(select(JobOpportunity).where(JobOpportunity.id == body["id"])) is not None
    assert db.scalars(select(JobApplication)).all() == []
    assert db.scalars(select(ApplicationEvent)).all() == []


def test_duplicate_url_returns_existing_record(api_context):
    _, user_a, _ = api_context
    client = client_for(user_a)
    first = client.post("/api/v1/opportunities", json=payload())
    second = client.post("/api/v1/opportunities", json=payload("https://careers.example.com/jobs/12345/"))
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_same_url_is_separate_for_each_user(api_context):
    _, user_a, user_b = api_context
    first = client_for(user_a).post("/api/v1/opportunities", json=payload())
    second = client_for(user_b).post("/api/v1/opportunities", json=payload())
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]


def test_invalid_url_and_missing_required_fields_are_rejected(api_context):
    _, user_a, _ = api_context
    client = client_for(user_a)
    assert client.post("/api/v1/opportunities", json={**payload(), "source_url": "javascript:alert(1)"}).status_code == 422
    assert client.post("/api/v1/opportunities", json={**payload(), "company_name": "   "}).status_code == 422
    assert client.post("/api/v1/opportunities", json={**payload(), "job_title": ""}).status_code == 422


def test_unauthenticated_import_is_rejected():
    response = TestClient(app).post("/api/v1/opportunities", json=payload())
    assert response.status_code == 401


def test_missing_csrf_is_rejected_with_real_auth_context(api_context):
    db, user_a, _ = api_context
    from app.services.auth_session_service import issue_session
    from app.core.config import get_settings

    token = issue_session(db, user=user_a, lifetime_days=7)
    db.flush()
    client = TestClient(app)
    client.cookies.set(get_settings().auth_cookie_name, token, path="/api/v1")
    response = client.post("/api/v1/opportunities", json=payload())
    assert response.status_code == 403


def test_cross_user_read_and_update_are_hidden(api_context):
    _, user_a, user_b = api_context
    created = client_for(user_a).post("/api/v1/opportunities", json=payload())
    opportunity_id = created.json()["id"]
    other = client_for(user_b)
    assert other.get(f"/api/v1/opportunities/{opportunity_id}").status_code == 404
    assert other.patch(f"/api/v1/opportunities/{opportunity_id}", json={"status": "ARCHIVED"}).status_code == 404


def test_list_filter_and_archive_preserve_record(api_context):
    _, user_a, _ = api_context
    client = client_for(user_a)
    created = client.post("/api/v1/opportunities", json=payload()).json()
    client.post("/api/v1/opportunities", json=payload("https://careers.example.com/jobs/67890"))
    archived = client.patch(f"/api/v1/opportunities/{created['id']}", json={"status": "ARCHIVED"})
    assert archived.status_code == 200
    assert client.get("/api/v1/opportunities?status=SAVED").json()["total"] == 1
    assert client.get("/api/v1/opportunities?status=ARCHIVED").json()["total"] == 1
    assert client.get("/api/v1/opportunities?page=1&page_size=1").json()["page_size"] == 1


def test_extra_fields_are_rejected(api_context):
    _, user_a, _ = api_context
    assert client_for(user_a).post("/api/v1/opportunities", json={**payload(), "submitted": True}).status_code == 422
