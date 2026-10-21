import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.dependencies.auth import get_current_user_id
from app.main import app
from app.models import ApplicationEvent, CandidateProfile, JobApplication, JobOpportunity


@pytest.fixture
def api_context():
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    user_a = __import__("app.models", fromlist=["User"]).User(email=f"match-a-{uuid.uuid4()}@example.com")
    user_b = __import__("app.models", fromlist=["User"]).User(email=f"match-b-{uuid.uuid4()}@example.com")
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


def opportunity_payload(url="https://jobs.example.com/java"):
    return {"company_name": "Example", "job_title": "Java Spring Boot Engineer", "description": "Build Java services with Spring Boot and PostgreSQL. US work authorization required.", "source_url": url}


def profile_payload(skills=None, version="resume-1"):
    return {"skills": skills or ["Java", "Spring Boot", "PostgreSQL"], "experience_summary": "Built Java and Spring Boot services", "target_roles": ["Engineer"], "preferred_locations": ["Boston"], "remote_preference": "HYBRID", "resume_version": version}


def test_profile_and_explainable_match(api_context):
    db, user_a, _ = api_context
    client = client_for(user_a)
    assert client.put("/api/v1/candidate-profile", json=profile_payload()).status_code == 200
    opportunity = client.post("/api/v1/opportunities", json=opportunity_payload()).json()
    response = client.post(f"/api/v1/opportunities/{opportunity['id']}/match")
    assert response.status_code == 200
    body = response.json()
    assert body["score"] is not None
    assert set(body["matched_skills"]) == {"java", "postgresql", "spring_boot"}
    assert "oracle_cpq" not in body["matched_skills"]
    assert body["eligibility_status"] == "NEEDS_REVIEW"
    assert db.scalars(select(JobApplication)).all() == []
    assert db.scalars(select(ApplicationEvent)).all() == []


def test_missing_description_is_insufficient_evidence(api_context):
    _, user_a, _ = api_context
    client = client_for(user_a)
    client.put("/api/v1/candidate-profile", json=profile_payload())
    opportunity = client.post("/api/v1/opportunities", json={"company_name": "Example", "job_title": "Engineer", "source_url": "https://jobs.example.com/no-description"}).json()
    result = client.post(f"/api/v1/opportunities/{opportunity['id']}/match").json()
    assert result["score"] is None
    assert result["ranking_status"] == "INSUFFICIENT_EVIDENCE"


def test_cross_user_match_access_is_rejected(api_context):
    _, user_a, user_b = api_context
    owner = client_for(user_a)
    owner.put("/api/v1/candidate-profile", json=profile_payload())
    opportunity = owner.post("/api/v1/opportunities", json=opportunity_payload()).json()
    assert client_for(user_b).post(f"/api/v1/opportunities/{opportunity['id']}/match").status_code == 404


def test_profile_revision_makes_previous_match_stale(api_context):
    _, user_a, _ = api_context
    client = client_for(user_a)
    client.put("/api/v1/candidate-profile", json=profile_payload())
    opportunity = client.post("/api/v1/opportunities", json=opportunity_payload("https://jobs.example.com/stale")).json()
    client.post(f"/api/v1/opportunities/{opportunity['id']}/match")
    client.put("/api/v1/candidate-profile", json=profile_payload(["Python"], "resume-2"))
    assert client.get(f"/api/v1/opportunities/{opportunity['id']}/match").status_code == 404


def test_identical_inputs_are_deterministic(api_context):
    _, user_a, _ = api_context
    client = client_for(user_a)
    client.put("/api/v1/candidate-profile", json=profile_payload())
    opportunity = client.post("/api/v1/opportunities", json=opportunity_payload("https://jobs.example.com/deterministic")).json()
    first = client.post(f"/api/v1/opportunities/{opportunity['id']}/match").json()
    second = client.post(f"/api/v1/opportunities/{opportunity['id']}/match").json()
    assert first["id"] == second["id"]
    assert first["score"] == second["score"]
    assert first["explanations"] == second["explanations"]
