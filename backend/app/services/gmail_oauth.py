from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.services.google_oauth import pkce_challenge

GMAIL_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
GMAIL_METADATA_SCOPE = "https://www.googleapis.com/auth/gmail.metadata"


class GmailOAuthError(Exception):
    pass


@dataclass(frozen=True)
class GmailGrant:
    access_token: str
    refresh_token: str | None
    granted_scopes: frozenset[str]
    expires_in: int | None


def build_gmail_consent_url(*, client_id: str, redirect_uri: str, state: str, verifier: str, scope: str = GMAIL_METADATA_SCOPE) -> str:
    return f"{GMAIL_AUTHORIZE_URL}?{urlencode({'client_id': client_id, 'redirect_uri': redirect_uri, 'response_type': 'code', 'scope': scope, 'state': state, 'code_challenge': pkce_challenge(verifier), 'code_challenge_method': 'S256', 'access_type': 'offline', 'prompt': 'consent'})}"


async def exchange_gmail_code(*, code: str, client_id: str, client_secret: str, redirect_uri: str, verifier: str) -> GmailGrant:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(GOOGLE_TOKEN_URL, data={'code': code, 'client_id': client_id, 'client_secret': client_secret, 'redirect_uri': redirect_uri, 'grant_type': 'authorization_code', 'code_verifier': verifier})
            response.raise_for_status()
            payload = response.json()
        scopes = frozenset(str(payload.get('scope', '')).split())
        access_token = payload.get('access_token')
        if not isinstance(access_token, str) or GMAIL_METADATA_SCOPE not in scopes:
            raise GmailOAuthError("Required Gmail permission was not granted")
        refresh_token = payload.get('refresh_token')
        return GmailGrant(access_token, refresh_token if isinstance(refresh_token, str) else None, scopes, payload.get('expires_in') if isinstance(payload.get('expires_in'), int) else None)
    except GmailOAuthError:
        raise
    except Exception as exc:
        raise GmailOAuthError("Gmail authorization failed") from exc


async def fetch_gmail_profile(access_token: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(GMAIL_PROFILE_URL, headers={'Authorization': f'Bearer {access_token}'})
            response.raise_for_status()
            email = response.json().get('emailAddress')
        if not isinstance(email, str) or not email:
            raise GmailOAuthError("Gmail mailbox could not be verified")
        return email
    except GmailOAuthError:
        raise
    except Exception as exc:
        raise GmailOAuthError("Gmail mailbox could not be verified") from exc
