import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.dependencies.auth import get_current_user_id
from app.main import app
from app.models import ApplicationEvent, ApplicationHandoff, JobApplication, User


@pytest.fixture
def api_context():
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    users = [User(email=f"handoff-{uuid.uuid4()}@example.com") for _ in range(2)]
    db.add_all(users)
    db.flush()
    app.dependency_overrides[get_db] = lambda: (yield db)
    try:
        yield db, users[0], users[1]
    finally:
        app.dependency_overrides.clear()
        db.close()
        transaction.rollback()
        connection.close()


def client_for(user):
    app.dependency_overrides[get_current_user_id] = lambda: user.id
    return TestClient(app)


def create_preparation(client):
    assert client.put("/api/v1/candidate-profile", json={"skills": ["Python"], "target_roles": ["Engineer"], "resume_version": "r1"}).status_code == 200
    opportunity = client.post("/api/v1/opportunities", json={"company_name": "Example", "job_title": "Engineer", "source_url": "https://jobs.example.com/engineer"}).json()
    return client.post(f"/api/v1/preparations/opportunities/{opportunity['id']}").json()


def approve(client, preparation):
    answers = [{"question_key": "work_authorization", "answer": "Yes", "status": "RESOLVED"}, {"question_key": "sponsorship", "answer": "No", "status": "RESOLVED"}]
    response = client.patch(f"/api/v1/preparations/{preparation['id']}", json={"application_answers": answers, "status": "APPROVED"})
    assert response.status_code == 200
    return response.json()


def test_handoff_does_not_create_application(api_context):
    db, user, _ = api_context
    client = client_for(user)
    preparation = approve(client, create_preparation(client))
    response = client.post(f"/api/v1/preparations/{preparation['id']}/handoff")
    assert response.status_code == 201
    assert db.scalars(select(ApplicationHandoff)).all()
    assert db.scalars(select(JobApplication)).all() == []
    assert db.scalars(select(ApplicationEvent)).all() == []


def test_draft_handoff_is_rejected(api_context):
    _, user, _ = api_context
    client = client_for(user)
    preparation = create_preparation(client)
    assert client.post(f"/api/v1/preparations/{preparation['id']}/handoff").status_code == 409


def test_confirmation_is_idempotent_and_creates_one_event(api_context):
    db, user, _ = api_context
    client = client_for(user)
    preparation = approve(client, create_preparation(client))
    handoff = client.post(f"/api/v1/preparations/{preparation['id']}/handoff").json()
    payload = {"expected_revision": preparation["draft_revision"], "idempotency_key": "confirm-1", "user_confirmed_submission": True, "handoff_id": handoff["id"]}
    first = client.post(f"/api/v1/preparations/{preparation['id']}/confirm-submission", json=payload)
    second = client.post(f"/api/v1/preparations/{preparation['id']}/confirm-submission", json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["job_application_id"] == second.json()["job_application_id"]
    assert len(db.scalars(select(JobApplication)).all()) == 1
    assert len(db.scalars(select(ApplicationEvent).where(ApplicationEvent.event_kind == "APPLICATION_SUBMITTED")).all()) == 1


def test_cross_user_confirmation_is_hidden(api_context):
    _, owner, other = api_context
    owner_client = client_for(owner)
    preparation = approve(owner_client, create_preparation(owner_client))
    other_client = client_for(other)
    assert other_client.post(f"/api/v1/preparations/{preparation['id']}/confirm-submission", json={"expected_revision": 1, "idempotency_key": "other", "user_confirmed_submission": True}).status_code == 404


def test_unresolved_answers_block_confirmation(api_context):
    _, user, _ = api_context
    client = client_for(user)
    preparation = client.post(f"/api/v1/preparations/opportunities/{create_preparation(client)['opportunity_id']}").json() if False else create_preparation(client)
    client.patch(f"/api/v1/preparations/{preparation['id']}", json={"status": "APPROVED"})
    response = client.post(f"/api/v1/preparations/{preparation['id']}/confirm-submission", json={"expected_revision": 1, "idempotency_key": "blocked", "user_confirmed_submission": True})
    assert response.status_code == 409