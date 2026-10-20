import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import AuthSession, OAuthLoginTransaction, User


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def create_user(db: Session, suffix: str | None = None) -> User:
    user = User(
        email=f"auth-{suffix or uuid.uuid4()}@example.com",
        display_name="Auth Test User",
    )
    db.add(user)
    db.flush()
    return user


def test_auth_tables_have_expected_columns_and_indexes():
    auth_columns = {column.name for column in inspect(AuthSession).columns}
    oauth_columns = {column.name for column in inspect(OAuthLoginTransaction).columns}

    assert {"user_id", "token_hash", "expires_at", "revoked_at"} <= auth_columns
    assert {"state_hash", "nonce", "pkce_code_verifier", "expires_at", "consumed_at"} <= oauth_columns
    assert {index.name for index in AuthSession.__table__.indexes} == {
        "ix_auth_sessions_user_id",
        "ix_auth_sessions_expires_at",
    }
    assert {index.name for index in OAuthLoginTransaction.__table__.indexes} == {
        "ix_oauth_login_transactions_expires_at",
    }


def test_google_subject_is_nullable_and_unique(db: Session):
    first = create_user(db, "google-one")
    second = create_user(db, "google-two")
    first.google_sub = "google-sub-1"
    second.google_sub = None
    db.flush()

    duplicate = User(email="auth-duplicate@example.com", google_sub="google-sub-1")
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(duplicate)
            db.flush()


def test_auth_session_stores_hash_and_belongs_to_user(db: Session):
    user = create_user(db, "session")
    token_hash = hashlib.sha256(b"session-token").digest()
    session = AuthSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(session)
    db.flush()

    stored = db.scalar(select(AuthSession).where(AuthSession.id == session.id))
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.token_hash == token_hash
    assert stored.revoked_at is None


def test_auth_session_token_hash_is_unique(db: Session):
    user = create_user(db, "duplicate-session")
    token_hash = hashlib.sha256(b"duplicate-token").digest()
    values = {
        "user_id": user.id,
        "token_hash": token_hash,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    }
    db.add(AuthSession(**values))
    db.flush()

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(AuthSession(**values))
            db.flush()


def test_oauth_transaction_state_hash_is_unique_and_expirable(db: Session):
    state_hash = hashlib.sha256(b"oauth-state").digest()
    values = {
        "state_hash": state_hash,
        "nonce": "nonce-value",
        "pkce_code_verifier": "pkce-verifier",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    transaction = OAuthLoginTransaction(**values)
    db.add(transaction)
    db.flush()
    assert transaction.expires_at > datetime.now(timezone.utc)

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(OAuthLoginTransaction(**values))
            db.flush()