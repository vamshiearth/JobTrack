from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth_cookies import clear_session_cookie, set_session_cookie
from app.core.config import get_settings
from app.db.session import get_db
from app.dependencies.auth import AuthContext, get_auth_context, get_current_user_id
from app.models import OAuthLoginTransaction
from app.services.google_identity import AccountLinkingRequired, resolve_google_user
from app.services.auth_session_service import csrf_for_session, issue_session, revoke_session
from app.services.google_oauth import (
    OAuthVerificationError,
    build_google_auth_url,
    exchange_authorization_code,
    generate_oauth_secrets,
    sha256_bytes,
    verify_google_identity,
)


router = APIRouter(prefix="/auth/google", tags=["Authentication"])
OAUTH_COOKIE = "jobtrack_oauth_state"
OAUTH_COOKIE_PATH = "/api/v1/auth/google/callback"


@router.get("/login")
def google_login(db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google authentication is not configured")

    state, nonce, verifier = generate_oauth_secrets()
    transaction = OAuthLoginTransaction(
        state_hash=sha256_bytes(state),
        nonce=nonce,
        pkce_code_verifier=verifier,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.auth_oauth_transaction_minutes),
    )
    db.add(transaction)
    db.commit()

    response = RedirectResponse(
        build_google_auth_url(
            client_id=settings.google_oauth_client_id,
            redirect_uri=settings.google_oauth_redirect_uri,
            state=state,
            nonce=nonce,
            verifier=verifier,
        ),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    response.set_cookie(
        OAUTH_COOKIE,
        state,
        max_age=settings.auth_oauth_transaction_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path=OAUTH_COOKIE_PATH,
    )
    return response


@router.get("/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    browser_state = request.cookies.get(OAUTH_COOKIE)
    if error or not code or not state or not browser_state or not secrets_compare(state, browser_state):
        return oauth_callback_error("Invalid OAuth callback")

    transaction = db.scalar(
        select(OAuthLoginTransaction)
        .where(OAuthLoginTransaction.state_hash == sha256_bytes(state))
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if transaction is None or transaction.consumed_at is not None or transaction.expires_at <= now:
        return oauth_callback_error("Invalid OAuth callback")

    transaction.consumed_at = now
    db.commit()

    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        return oauth_callback_error("Google authentication is not configured", status.HTTP_503_SERVICE_UNAVAILABLE)
    try:
        token_response = await exchange_authorization_code(
            code=code,
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
            redirect_uri=settings.google_oauth_redirect_uri,
            verifier=transaction.pkce_code_verifier,
        )
        claims = verify_google_identity(
            token=str(token_response["id_token"]),
            client_id=settings.google_oauth_client_id,
            expected_nonce=transaction.nonce,
        )
        user = resolve_google_user(
            db,
            subject=claims["sub"],
            email=claims["email"],
            display_name=claims["display_name"],
        )
        raw_session_token = issue_session(
            db, user=user, lifetime_days=settings.auth_session_days
        )
        db.commit()
    except AccountLinkingRequired:
        db.rollback()
        return oauth_callback_error("ACCOUNT_LINKING_REQUIRED", 409)
    except IntegrityError:
        db.rollback()
        return oauth_callback_error("ACCOUNT_CONFLICT", 409)
    except (OAuthVerificationError, KeyError):
        db.rollback()
        return oauth_callback_error("Google identity verification failed")

    response = RedirectResponse(
        settings.auth_frontend_url.rstrip("/"), status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie(OAUTH_COOKIE, path=OAUTH_COOKIE_PATH)
    set_session_cookie(response, raw_session_token)
    return response


def oauth_callback_error(detail: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> JSONResponse:
    response = JSONResponse({"detail": detail}, status_code=status_code)
    response.delete_cookie(OAUTH_COOKIE, path=OAUTH_COOKIE_PATH)
    return response


def secrets_compare(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left, right)


session_router = APIRouter(prefix="/auth", tags=["Authentication"])


@session_router.get("/me")
def get_authenticated_user(context: AuthContext = Depends(get_auth_context)):
    response = JSONResponse(
        {
            "id": str(context.user.id),
            "email": context.user.email,
            "display_name": context.user.display_name,
            "csrf_token": csrf_for_session(context.raw_token),
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@session_router.post("/logout")
def logout(
    context: AuthContext = Depends(get_auth_context),
    _user_id=Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        revoke_session(db, context.session)
        db.commit()
    except Exception:
        db.rollback()
        raise
    response = JSONResponse({"logged_out": True})
    clear_session_cookie(response)
    return response