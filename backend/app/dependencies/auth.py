import secrets
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import AuthSession, User
from app.services.auth_session_service import csrf_for_session, find_active_session


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass
class AuthContext:
    session: AuthSession
    user: User
    raw_token: str


def get_auth_context(
    request: Request, db: Session = Depends(get_db)
) -> AuthContext:
    settings = get_settings()
    raw_token = request.cookies.get(settings.auth_cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    found = find_active_session(db, raw_token)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session, user = found

    if request.method not in SAFE_METHODS:
        origin = request.headers.get("origin")
        trusted_origins = {
            configured.rstrip("/") for configured in settings.auth_trusted_origins
        }
        trusted_origins.add(settings.auth_frontend_url.rstrip("/"))
        if origin not in trusted_origins:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trusted origin required")
        csrf_token = request.headers.get("x-csrf-token")
        if not csrf_token or not secrets.compare_digest(csrf_token, csrf_for_session(raw_token)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")

    return AuthContext(session=session, user=user, raw_token=raw_token)


def get_current_user_id(context: AuthContext = Depends(get_auth_context)) -> UUID:
    return context.user.id