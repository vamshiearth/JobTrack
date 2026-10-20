import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class OAuthVerificationError(Exception):
    pass


def sha256_bytes(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def generate_oauth_secrets() -> tuple[str, str, str]:
    return (
        secrets.token_urlsafe(32),
        secrets.token_urlsafe(32),
        secrets.token_urlsafe(64),
    )


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def build_google_auth_url(*, client_id: str, redirect_uri: str, state: str, nonce: str, verifier: str) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
            "access_type": "offline",
        }
    )
    return f"{GOOGLE_AUTHORIZE_URL}?{query}"


async def exchange_authorization_code(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    verifier: str,
) -> dict[str, object]:
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        raise OAuthVerificationError("Google authorization failed") from exc


def verify_google_identity(*, token: str, client_id: str, expected_nonce: str) -> dict[str, str]:
    try:
        claims = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id,
        )
    except Exception as exc:
        raise OAuthVerificationError("Google identity verification failed") from exc

    if claims.get("nonce") != expected_nonce:
        raise OAuthVerificationError("Google identity verification failed")
    if claims.get("email_verified") is not True:
        raise OAuthVerificationError("Google identity verification failed")

    subject = claims.get("sub")
    email = claims.get("email")
    if not isinstance(subject, str) or not isinstance(email, str):
        raise OAuthVerificationError("Google identity verification failed")
    display_name = claims.get("name")
    return {
        "sub": subject,
        "email": email,
        "display_name": display_name if isinstance(display_name, str) else email,
    }