import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.dependencies.auth import get_current_user_id
from app.main import app
from app.models import ApplicationEvent, ApplicationPreparation, JobApplication, User


@pytest.fixture
def api_context():
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    user_a = User(email=f"prep-a-{uuid.uuid4()}@example.com")
    user_b = User(email=f"prep-b-{uuid.uuid4()}@example.com")
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


def profile():
    return {"skills": ["Java", "Spring Boot"], "experience_summary": "Built Java Spring Boot services", "target_roles": ["Engineer"], "resume_version": "resume-1"}


def opportunity():
    return {"company_name": "Example", "job_title": "Java Engineer", "description": "Build Java and Spring Boot services.", "source_url": "https://jobs.example.com/prep"}


def create_inputs(client):
    assert client.put("/api/v1/candidate-profile", json=profile()).status_code == 200
    response = client.post("/api/v1/opportunities", json=opportunity())
    assert response.status_code == 201
    return response.json()["id"]


def test_prepare_generates_truthful_reviewable_package_without_application(api_context):
    db, user_a, _ = api_context
    client = client_for(user_a)
    opportunity_id = create_inputs(client)
    response = client.post(f"/api/v1/preparations/opportunities/{opportunity_id}")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "NEEDS_REVIEW"
    assert body["resume_suggestions"][0]["source_evidence_id"].startswith("candidate_profile:")
    assert all(answer["answer"] is None for answer in body["application_answers"])
    assert db.scalars(select(JobApplication)).all() == []
    assert db.scalars(select(ApplicationEvent)).all() == []


def test_approval_requires_current_package_and_records_revision(api_context):
    _, user_a, _ = api_context
    client = client_for(user_a)
    opportunity_id = create_inputs(client)
    preparation = client.post(f"/api/v1/preparations/opportunities/{opportunity_id}").json()
    approved = client.patch(f"/api/v1/preparations/{preparation['id']}", json={"status": "APPROVED"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["approved_revision"] == 1


def test_editing_package_returns_it_to_review(api_context):
    _, user_a, _ = api_context
    client = client_for(user_a)
    opportunity_id = create_inputs(client)
    preparation = client.post(f"/api/v1/preparations/opportunities/{opportunity_id}").json()
    client.patch(f"/api/v1/preparations/{preparation['id']}", json={"status": "APPROVED"})
    updated = client.patch(f"/api/v1/preparations/{preparation['id']}", json={"review_notes": "Please verify this."})
    assert updated.status_code == 200
    assert updated.json()["status"] == "NEEDS_REVIEW"
    assert updated.json()["approved_at"] is None


def test_cross_user_preparation_is_hidden(api_context):
    _, user_a, user_b = api_context
    owner = client_for(user_a)
    opportunity_id = create_inputs(owner)
    preparation = owner.post(f"/api/v1/preparations/opportunities/{opportunity_id}").json()
    assert client_for(user_b).get(f"/api/v1/preparations/{preparation['id']}").status_code == 404


def test_stale_profile_invalidates_preparation_approval(api_context):
    _, user_a, _ = api_context
    client = client_for(user_a)
    opportunity_id = create_inputs(client)
    preparation = client.post(f"/api/v1/preparations/opportunities/{opportunity_id}").json()
    client.patch(f"/api/v1/preparations/{preparation['id']}", json={"status": "APPROVED"})
    client.put("/api/v1/candidate-profile", json={**profile(), "resume_version": "resume-2"})
    current = client.get(f"/api/v1/preparations/{preparation['id']}")
    assert current.status_code == 200
    assert current.json()["status"] == "STALE"
