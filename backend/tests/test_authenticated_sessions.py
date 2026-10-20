import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine, get_db
from app.dependencies.auth import get_current_user_id
from app.main import app
from app.models import ApplicationEvent, AuthSession, JobApplication, User
from app.services.auth_session_service import csrf_for_session, hash_session_token, issue_session


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


def session_for(db: Session, user: User, days: int = 7) -> str:
    token = issue_session(db, user=user, lifetime_days=days)
    db.flush()
    return token


def client_for(token: str) -> TestClient:
    client = TestClient(app)
    client.cookies.set(get_settings().auth_cookie_name, token, path="/api/v1")
    return client


def test_session_token_is_random_and_only_hash_is_stored(context):
    user = create_user(context, "session")
    token = session_for(context, user)
    stored = context.scalar(select(AuthSession).where(AuthSession.user_id == user.id))
    assert len(token) > 32
    assert stored is not None
    assert stored.token_hash == hash_session_token(token)
    assert token.encode() not in stored.token_hash


def test_me_returns_user_and_session_bound_csrf(context):
    user = create_user(context, "me")
    token = session_for(context, user)
    with client_for(token) as client:
        response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.json()["csrf_token"] == csrf_for_session(token)
    assert token not in response.text


def test_missing_or_invalid_session_is_unauthorized(context):
    with TestClient(app) as client:
        missing = client.get("/api/v1/auth/me")
        client.cookies.set(get_settings().auth_cookie_name, "invalid")
        invalid = client.get("/api/v1/auth/me")
    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_authenticated_write_requires_origin_and_csrf(context):
    user = create_user(context, "csrf")
    token = session_for(context, user)
    payload = {"company_name": "Acme", "job_title": "Engineer"}
    with client_for(token) as client:
        missing_origin = client.post("/api/v1/applications", json=payload, headers={"X-CSRF-Token": csrf_for_session(token)})
        missing_csrf = client.post("/api/v1/applications", json=payload, headers={"Origin": "http://localhost:5173"})
        valid = client.post("/api/v1/applications", json=payload, headers={"Origin": "http://localhost:5173", "X-CSRF-Token": csrf_for_session(token)})
    assert missing_origin.status_code == 403
    assert missing_csrf.status_code == 403
    assert valid.status_code == 201


def test_missing_origin_blocks_authenticated_write(context):
    user = create_user(context, "missing-origin")
    token = session_for(context, user)
    with client_for(token) as client:
        response = client.post(
            "/api/v1/applications",
            json={"company_name": "Example", "job_title": "Developer"},
            headers={"X-CSRF-Token": csrf_for_session(token)},
        )
    assert response.status_code == 403


def test_wrong_csrf_token_blocks_write(context):
    user = create_user(context, "wrong-csrf")
    token = session_for(context, user)
    with client_for(token) as client:
        response = client.post(
            "/api/v1/applications",
            json={"company_name": "Example", "job_title": "Developer"},
            headers={"Origin": "http://localhost:5173", "X-CSRF-Token": "not-the-correct-token"},
        )
    assert response.status_code == 403


def test_csrf_token_cannot_cross_sessions(context):
    user_a = create_user(context, "csrf-a")
    user_b = create_user(context, "csrf-b")
    token_a = session_for(context, user_a)
    token_b = session_for(context, user_b)
    payload = {"company_name": "Acme", "job_title": "Engineer"}
    with client_for(token_b) as client:
        response = client.post(
            "/api/v1/applications",
            json=payload,
            headers={"Origin": "http://localhost:5173", "X-CSRF-Token": csrf_for_session(token_a)},
        )
    assert response.status_code == 403


def test_expired_session_is_unauthorized(context):
    user = create_user(context, "expired")
    token = session_for(context, user)
    stored = context.scalar(select(AuthSession).where(AuthSession.user_id == user.id))
    stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    context.flush()
    with client_for(token) as client:
        response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_logout_revokes_session_and_clears_cookie(context):
    user = create_user(context, "logout")
    token = session_for(context, user)
    with client_for(token) as client:
        me = client.get("/api/v1/auth/me")
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://localhost:5173", "X-CSRF-Token": me.json()["csrf_token"]},
        )
        after = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert after.status_code == 401


def test_user_cannot_read_another_users_applications(context):
    user_a = create_user(context, "owner")
    user_b = create_user(context, "other")
    application = JobApplication(
        user_id=user_a.id,
        company_name="Private Co",
        job_title="Engineer",
        application_source="MANUAL",
        current_stage="APPLIED",
        next_action_owner="NONE",
        last_activity_at=datetime.now(timezone.utc),
    )
    context.add(application)
    context.flush()
    token_b = session_for(context, user_b)
    with client_for(token_b) as client:
        response = client.get(f"/api/v1/applications/{application.id}")
    assert response.status_code == 404