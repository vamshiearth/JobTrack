import httpx

from app.services.gmail_oauth import GOOGLE_TOKEN_URL


class GmailTokenRefreshError(Exception):
    pass


def refresh_gmail_access_token(*, client_id: str, client_secret: str, refresh_token: str) -> str:
    if not client_id or not client_secret or not refresh_token:
        raise GmailTokenRefreshError("Gmail credentials are unavailable")
    try:
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            response = client.post(GOOGLE_TOKEN_URL, data={"client_id": client_id, "client_secret": client_secret, "refresh_token": refresh_token, "grant_type": "refresh_token"})
        if response.status_code >= 400:
            raise GmailTokenRefreshError("Gmail credential refresh failed")
        payload = response.json()
        access_token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(access_token, str) or not access_token:
            raise GmailTokenRefreshError("Gmail credential refresh failed")
        return access_token
    except GmailTokenRefreshError:
        raise
    except Exception as exc:
        raise GmailTokenRefreshError("Gmail credential refresh failed") from exc
