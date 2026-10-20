import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.dependencies.auth import AuthContext, get_auth_context
from app.models import GmailConnection, GmailOAuthTransaction
from app.services.gmail_oauth import (
    GMAIL_METADATA_SCOPE,
    GmailOAuthError,
    build_gmail_consent_url,
    exchange_gmail_code,
    fetch_gmail_profile,
)
from app.services.gmail_token_crypto import get_gmail_token_crypto
from app.services.google_oauth import generate_oauth_secrets, sha256_bytes

router = APIRouter(prefix="/gmail", tags=["Gmail"])
CONSENT_COOKIE = "jobtrack_gmail_consent"
CONSENT_COOKIE_PATH = "/api/v1/gmail/callback"


def callback_error(detail: str, code: int = 400) -> JSONResponse:
    response = JSONResponse({"detail": detail}, status_code=code)
    response.delete_cookie(CONSENT_COOKIE, path=CONSENT_COOKIE_PATH)
    return response


@router.get("/connection")
def connection(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    item = db.scalar(select(GmailConnection).where(GmailConnection.user_id == context.user.id, GmailConnection.connection_status != "DISCONNECTED"))
    if item is None:
        return {"connected": False, "email": None, "status": "DISCONNECTED", "granted_scopes": [], "last_synced_at": None}
    return {"connected": True, "email": item.email_address, "status": item.connection_status, "granted_scopes": item.granted_scopes, "last_synced_at": item.sync_state.last_successful_sync_at if item.sync_state else None}


@router.post("/connect")
def connect(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.gmail_oauth_client_id or not settings.gmail_oauth_client_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Gmail authorization is not configured")
    state, nonce, verifier = generate_oauth_secrets()
    transaction = GmailOAuthTransaction(user_id=context.user.id, auth_session_id=context.session.id, state_hash=sha256_bytes(state), nonce=nonce, pkce_code_verifier=verifier, expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.auth_oauth_transaction_minutes))
    db.add(transaction)
    db.commit()
    response = JSONResponse({"authorization_url": build_gmail_consent_url(client_id=settings.gmail_oauth_client_id, redirect_uri=settings.gmail_oauth_redirect_uri, state=state, verifier=verifier)})
    response.set_cookie(CONSENT_COOKIE, state, max_age=settings.auth_oauth_transaction_minutes * 60, httponly=True, secure=settings.auth_cookie_secure, samesite="lax", path=CONSENT_COOKIE_PATH)
    return response


@router.get("/callback")
async def callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    if error or not code or not state:
        return callback_error("Gmail authorization was not completed")
    browser_state = request.cookies.get(CONSENT_COOKIE)
    if not browser_state or not secrets.compare_digest(state, browser_state):
        return callback_error("Invalid Gmail authorization callback")
    settings = get_settings()
    raw_token = request.cookies.get(settings.auth_cookie_name)
    if not raw_token:
        return callback_error("Authentication required", 401)
    from app.services.auth_session_service import find_active_session
    found = find_active_session(db, raw_token)
    if found is None:
        return callback_error("Authentication required", 401)
    session, user = found
    transaction = db.scalar(select(GmailOAuthTransaction).where(GmailOAuthTransaction.state_hash == sha256_bytes(state)).with_for_update())
    now = datetime.now(timezone.utc)
    if transaction is None or transaction.consumed_at is not None or transaction.expires_at <= now or transaction.user_id != user.id or transaction.auth_session_id != session.id:
        return callback_error("Invalid Gmail authorization callback")
    transaction.consumed_at = now
    db.commit()
    try:
        if not settings.gmail_oauth_client_id or not settings.gmail_oauth_client_secret:
            raise GmailOAuthError("Gmail authorization is not configured")
        grant = await exchange_gmail_code(code=code, client_id=settings.gmail_oauth_client_id, client_secret=settings.gmail_oauth_client_secret, redirect_uri=settings.gmail_oauth_redirect_uri, verifier=transaction.pkce_code_verifier)
        email = await fetch_gmail_profile(grant.access_token)
        existing = db.scalar(select(GmailConnection).where(GmailConnection.user_id == user.id, GmailConnection.connection_status != "DISCONNECTED"))
        if grant.refresh_token is None and existing is None:
            raise GmailOAuthError("Gmail authorization did not provide a refresh credential")
        if existing is not None and existing.email_address != email:
            raise GmailOAuthError("Gmail mailbox does not match the existing connection")
        if existing is None:
            existing = GmailConnection(user_id=user.id, google_subject=email, email_address=email, encrypted_refresh_token=get_gmail_token_crypto().encrypt(grant.refresh_token), granted_scopes=sorted(grant.granted_scopes), connection_status="CONNECTED")
            db.add(existing)
        elif grant.refresh_token is not None:
            existing.encrypted_refresh_token = get_gmail_token_crypto().encrypt(grant.refresh_token)
        existing.granted_scopes = sorted(grant.granted_scopes)
        existing.connection_status = "CONNECTED"
        existing.disconnected_at = None
        db.commit()
    except (GmailOAuthError, KeyError):
        db.rollback()
        return callback_error("Gmail authorization could not be completed")
    response = RedirectResponse(settings.auth_frontend_url.rstrip("/") + "/settings", status_code=303)
    response.delete_cookie(CONSENT_COOKIE, path=CONSENT_COOKIE_PATH)
    return response


@router.post("/disconnect")
def disconnect(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    item = db.scalar(select(GmailConnection).where(GmailConnection.user_id == context.user.id, GmailConnection.connection_status != "DISCONNECTED"))
    if item is not None:
        item.connection_status = "DISCONNECTED"
        item.encrypted_refresh_token = None
        item.disconnected_at = datetime.now(timezone.utc)
    db.execute(update(GmailOAuthTransaction).where(GmailOAuthTransaction.user_id == context.user.id, GmailOAuthTransaction.consumed_at.is_(None)).values(consumed_at=datetime.now(timezone.utc)))
    db.commit()
    return {"status": "DISCONNECTED"}
