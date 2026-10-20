import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthSession, User


def hash_session_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii")).digest()


def csrf_for_session(token: str) -> str:
    return hmac.new(
        token.encode("ascii"), b"jobtrack-csrf-v1", hashlib.sha256
    ).hexdigest()


def issue_session(db: Session, *, user: User, lifetime_days: int = 7) -> str:
    if not 1 <= lifetime_days <= 7:
        raise ValueError("Invalid session lifetime")
    raw_token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=lifetime_days),
        )
    )
    return raw_token


def find_active_session(db: Session, raw_token: str) -> tuple[AuthSession, User] | None:
    session_and_user = db.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(
            AuthSession.token_hash == hash_session_token(raw_token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
    ).first()
    return session_and_user


def revoke_session(db: Session, session: AuthSession) -> None:
    session.revoked_at = datetime.now(timezone.utc)