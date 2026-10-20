import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1 import auth
from app.db.session import engine, get_db
from app.main import app
from app.models import OAuthLoginTransaction, User
from app.services.google_oauth import (
    OAuthVerificationError,
    generate_oauth_secrets,
    pkce_challenge,
    verify_google_identity,
)


@pytest.fixture
def db_context():
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        yield db
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def oauth_settings(monkeypatch):
    settings = SimpleNamespace(
        google_oauth_client_id="test-client",
        google_oauth_client_secret="test-secret",
        google_oauth_redirect_uri="http://localhost:8000/api/v1/auth/google/callback",
        auth_oauth_transaction_minutes=10,
        auth_cookie_secure=False,
        auth_cookie_name="jobtrack_session",
        auth_session_days=7,
        auth_frontend_url="http://localhost:5173",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    return settings


def test_pkce_challenge_and_secret_generation():
    state, nonce, verifier = generate_oauth_secrets()
    assert state and nonce and verifier
    assert pkce_challenge(verifier)
    assert len({state, nonce, verifier}) == 3


def test_login_redirect_stores_browser_bound_transaction(db_context, oauth_settings):
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/google/login", follow_redirects=False)

    assert response.status_code == 307
    location = response.headers["location"]
    query = parse_qs(urlparse(location).query)
    state = query["state"][0]
    assert query["scope"] == ["openid email profile"]
    assert query["code_challenge_method"] == ["S256"]
    assert response.cookies[auth.OAUTH_COOKIE]
    transaction = db_context.scalar(
        select(OAuthLoginTransaction).where(
            OAuthLoginTransaction.state_hash == hashlib.sha256(state.encode()).digest()
        )
    )
    assert transaction is not None
    assert transaction.consumed_at is None


def test_callback_rejects_missing_or_mismatched_browser_state(db_context, oauth_settings):
    with TestClient(app) as client:
        missing = client.get("/api/v1/auth/google/callback?code=code&state=state")
        client.cookies.set(auth.OAUTH_COOKIE, "different")
        mismatched = client.get("/api/v1/auth/google/callback?code=code&state=state")

    assert missing.status_code == 400
    assert mismatched.status_code == 400


def test_callback_consumes_transaction_before_exchange(db_context, oauth_settings, monkeypatch):
    state, nonce, verifier = generate_oauth_secrets()
    transaction = OAuthLoginTransaction(
        state_hash=hashlib.sha256(state.encode()).digest(),
        nonce=nonce,
        pkce_code_verifier=verifier,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db_context.add(transaction)
    db_context.flush()
    monkeypatch.setattr(auth, "exchange_authorization_code", lambda **kwargs: (_ for _ in ()).throw(auth.OAuthVerificationError("exchange failed")))

    with TestClient(app) as client:
        client.cookies.set(auth.OAUTH_COOKIE, state)
        response = client.get(
            f"/api/v1/auth/google/callback?code=code&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert db_context.get(OAuthLoginTransaction, transaction.id).consumed_at is not None


def test_callback_replay_and_expired_transaction_are_rejected(db_context, oauth_settings):
    state, nonce, verifier = generate_oauth_secrets()
    transaction = OAuthLoginTransaction(
        state_hash=hashlib.sha256(state.encode()).digest(),
        nonce=nonce,
        pkce_code_verifier=verifier,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db_context.add(transaction)
    db_context.flush()

    with TestClient(app) as client:
        client.cookies.set(auth.OAUTH_COOKIE, state)
        response = client.get(
            f"/api/v1/auth/google/callback?code=code&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert transaction.consumed_at is None


def test_verified_identity_creates_session_and_me_returns_user(db_context, oauth_settings, monkeypatch):
    state, nonce, verifier = generate_oauth_secrets()
    transaction = OAuthLoginTransaction(
        state_hash=hashlib.sha256(state.encode()).digest(),
        nonce=nonce,
        pkce_code_verifier=verifier,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db_context.add(transaction)
    db_context.flush()
    async def exchange_code(**kwargs):
        return {"id_token": "token"}

    monkeypatch.setattr(auth, "exchange_authorization_code", exchange_code)
    monkeypatch.setattr(
        auth,
        "verify_google_identity",
        lambda **kwargs: {"sub": "google-sub", "email": "new@example.com", "display_name": "New User"},
    )

    with TestClient(app) as client:
        client.cookies.set(auth.OAUTH_COOKIE, state)
        response = client.get(
            f"/api/v1/auth/google/callback?code=code&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:5173"
    cookie_header = response.headers["set-cookie"]
    assert "jobtrack_session=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/api/v1" in cookie_header
    assert "SameSite=lax" in cookie_header
    assert response.cookies.get(auth.OAUTH_COOKIE) is None
    with TestClient(app) as client:
        client.cookies.update(response.cookies)
        me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"
    assert me.json()["csrf_token"]
    assert db_context.scalar(select(User).where(User.google_sub == "google-sub")) is not None


def test_nonce_and_email_verification_are_required(monkeypatch):
    def verified(*args, **kwargs):
        return {"sub": "google-sub", "email": "test@example.com", "email_verified": True, "nonce": "correct"}

    monkeypatch.setattr("app.services.google_oauth.id_token.verify_oauth2_token", verified)
    with pytest.raises(OAuthVerificationError):
        verify_google_identity(token="token", client_id="client", expected_nonce="wrong")

    def unverified(*args, **kwargs):
        claims = verified()
        claims["email_verified"] = False
        return claims

    monkeypatch.setattr("app.services.google_oauth.id_token.verify_oauth2_token", unverified)
    with pytest.raises(OAuthVerificationError):
        verify_google_identity(token="token", client_id="client", expected_nonce="correct")


def test_existing_email_requires_explicit_account_linking(db_context):
    from app.services.google_identity import AccountLinkingRequired, resolve_google_user

    user = User(email="existing@example.com", display_name="Existing")
    db_context.add(user)
    db_context.flush()
    with pytest.raises(AccountLinkingRequired):
        resolve_google_user(
            db_context,
            subject="new-google-sub",
            email=user.email,
            display_name="Existing",
        )
