import uuid
from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import GmailConnection, GmailSyncState, User
from app.services.gmail_token_crypto import GmailTokenCrypto


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def create_user(db: Session, label: str) -> User:
    user = User(email=f"{label}-{uuid.uuid4()}@example.com", display_name=label)
    db.add(user)
    db.flush()
    return user


def create_connection(db: Session, user: User, status: str = "CONNECTED") -> GmailConnection:
    connection = GmailConnection(
        user_id=user.id,
        google_subject=f"google-{uuid.uuid4()}",
        email_address=f"gmail-{uuid.uuid4()}@example.com",
        encrypted_refresh_token=None,
        granted_scopes=["https://www.googleapis.com/auth/gmail.metadata"],
        connection_status=status,
    )
    db.add(connection)
    db.flush()
    return connection


def test_encrypted_refresh_token_persists_without_plaintext(db: Session):
    user = create_user(db, "credential")
    crypto = GmailTokenCrypto([Fernet.generate_key().decode("ascii")])
    plaintext = "fictional-refresh-token"
    ciphertext = crypto.encrypt(plaintext)
    connection = create_connection(db, user)
    connection.encrypted_refresh_token = ciphertext
    db.flush()
    db.expire_all()

    stored = db.scalar(select(GmailConnection).where(GmailConnection.id == connection.id))

    assert stored is not None
    assert stored.encrypted_refresh_token == ciphertext
    assert plaintext.encode("utf-8") not in stored.encrypted_refresh_token
    assert crypto.decrypt(stored.encrypted_refresh_token) == plaintext


def test_sync_state_is_one_to_one_with_connection(db: Session):
    user = create_user(db, "sync")
    connection = create_connection(db, user)
    sync_state = GmailSyncState(
        gmail_connection_id=connection.id,
        sync_status="IDLE",
        last_history_id=None,
        last_successful_sync_at=None,
    )
    db.add(sync_state)
    db.flush()

    stored = db.get(GmailSyncState, connection.id)

    assert stored is not None
    assert stored.gmail_connection_id == connection.id
    assert stored.sync_status == "IDLE"


def test_connection_requires_existing_user(db: Session):
    connection = GmailConnection(
        user_id=uuid.uuid4(),
        google_subject="fictional-subject",
        email_address="fictional@example.com",
        granted_scopes=[],
        connection_status="DISCONNECTED",
    )
    db.add(connection)

    with pytest.raises(IntegrityError):
        db.flush()


def test_active_connection_uniqueness_is_preserved(db: Session):
    user = create_user(db, "unique")
    create_connection(db, user)
    duplicate = GmailConnection(
        user_id=user.id,
        google_subject="another-subject",
        email_address="another@example.com",
        granted_scopes=[],
        connection_status="CONNECTED",
    )
    db.add(duplicate)

    with pytest.raises(IntegrityError):
        db.flush()


def test_disconnected_connection_may_have_no_credential(db: Session):
    user = create_user(db, "disconnected")
    connection = create_connection(db, user, status="DISCONNECTED")
    connection.disconnected_at = datetime.now(timezone.utc)
    db.flush()

    assert connection.encrypted_refresh_token is None
    assert connection.connection_status == "DISCONNECTED"
