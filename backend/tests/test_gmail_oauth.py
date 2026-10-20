import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine, get_db
from app.dependencies.auth import get_auth_context
from app.main import app
from app.models import AuthSession, GmailOAuthTransaction, User
from app.services.auth_session_service import csrf_for_session, issue_session
from app.services.gmail_oauth import GMAIL_METADATA_SCOPE, build_gmail_consent_url


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


def create_user(db: Session) -> User:
    user = User(email=f"gmail-{uuid.uuid4()}@example.com", display_name="Gmail Test")
    db.add(user)
    db.flush()
    return user


def client_for(db: Session, user: User) -> tuple[TestClient, str]:
    token = issue_session(db, user=user, lifetime_days=7)
    db.flush()
    client = TestClient(app)
    client.cookies.set(get_settings().auth_cookie_name, token, path="/api/v1")
    return client, csrf_for_session(token)


def test_consent_url_requests_only_metadata():
    url = build_gmail_consent_url(client_id="client", redirect_uri="http://localhost/callback", state="state", verifier="verifier")
    query = parse_qs(urlparse(url).query)
    assert query["scope"] == [GMAIL_METADATA_SCOPE]
    assert query["access_type"] == ["offline"]
    assert query["code_challenge_method"] == ["S256"]


def test_connect_requires_authentication(context):
    with TestClient(app) as client:
        response = client.post("/api/v1/gmail/connect", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 401


def test_connect_requires_csrf(context):
    user = create_user(context)
    client, _ = client_for(context, user)
    with client:
        response = client.post("/api/v1/gmail/connect", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 403


def test_connect_binds_transaction_to_user_and_session(monkeypatch, context):
    user = create_user(context)
    client, csrf = client_for(context, user)
    settings = get_settings()
    monkeypatch.setattr(settings, "gmail_oauth_client_id", "client-id")
    monkeypatch.setattr(settings, "gmail_oauth_client_secret", "client-secret")
    with client:
        response = client.post("/api/v1/gmail/connect", headers={"Origin": "http://localhost:5173", "X-CSRF-Token": csrf})
    assert response.status_code == 200
    transaction = context.query(GmailOAuthTransaction).one()
    session = context.query(AuthSession).filter_by(user_id=user.id).one()
    assert transaction.user_id == user.id
    assert transaction.auth_session_id == session.id
    assert transaction.pkce_code_verifier not in response.text
    assert "refresh" not in response.text.lower()


def test_connection_status_exposes_metadata_only(context):
    user = create_user(context)
    client, _ = client_for(context, user)
    with client:
        response = client.get("/api/v1/gmail/connection")
    assert response.status_code == 200
    assert response.json() == {"connected": False, "email": None, "status": "DISCONNECTED", "granted_scopes": [], "last_synced_at": None}
