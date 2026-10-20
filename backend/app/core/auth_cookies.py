from fastapi import Response

from app.core.config import get_settings


COOKIE_PATH = "/api/v1"
COOKIE_SAMESITE = "lax"


def set_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=raw_token,
        max_age=settings.auth_session_days * 86400,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=COOKIE_SAMESITE,
    )
    response.headers["Cache-Control"] = "no-store"


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path=COOKIE_PATH,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=COOKIE_SAMESITE,
    )
    response.headers["Cache-Control"] = "no-store"