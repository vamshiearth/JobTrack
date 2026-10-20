from dataclasses import dataclass
from typing import Any

import httpx

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
METADATA_HEADERS = ("From", "To", "Subject", "Date", "Message-ID")


class GmailAPIError(Exception):
    pass


class GmailHistoryExpired(GmailAPIError):
    pass


@dataclass(frozen=True)
class GmailMessageMetadata:
    message_id: str
    thread_id: str
    history_id: str | None
    internal_date_ms: int | None
    labels: tuple[str, ...]
    headers: dict[str, str]


def parse_message_metadata(payload: dict[str, Any]) -> GmailMessageMetadata:
    message_id = payload.get("id")
    thread_id = payload.get("threadId")
    if not isinstance(message_id, str) or not message_id or not isinstance(thread_id, str) or not thread_id:
        raise ValueError("Invalid Gmail message metadata")
    raw_headers = payload.get("payload", {}).get("headers", [])
    if not isinstance(raw_headers, list):
        raise ValueError("Invalid Gmail headers")
    allowed = {name.lower() for name in METADATA_HEADERS}
    headers: dict[str, str] = {}
    for header in raw_headers:
        if isinstance(header, dict) and isinstance(header.get("name"), str) and isinstance(header.get("value"), str) and header["name"].lower() in allowed:
            headers[header["name"].lower()] = header["value"]
    internal_date = payload.get("internalDate")
    return GmailMessageMetadata(message_id, thread_id, payload.get("historyId") if isinstance(payload.get("historyId"), str) else None, int(internal_date) if isinstance(internal_date, str) and internal_date.isdigit() else None, tuple(label for label in payload.get("labelIds", []) if isinstance(label, str)), headers)


class GmailMetadataClient:
    def __init__(self, access_token: str, *, timeout: float = 10.0):
        self._client = httpx.Client(timeout=timeout, follow_redirects=False, headers={"Authorization": f"Bearer {access_token}"})

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        response = self._client.get(f"{GMAIL_API_BASE}/{path}", params=params)
        if response.status_code == 404 and path.startswith("history"):
            raise GmailHistoryExpired("Gmail history cursor expired")
        if response.status_code >= 400:
            raise GmailAPIError("Gmail metadata request failed")
        payload = response.json()
        if not isinstance(payload, dict):
            raise GmailAPIError("Invalid Gmail response")
        return payload

    def profile(self) -> dict[str, Any]:
        return self._get("profile")

    def list_messages(self, *, page_token: str | None = None, max_results: int = 100) -> dict[str, Any]:
        params = {"maxResults": str(max_results)}
        if page_token:
            params["pageToken"] = page_token
        return self._get("messages", params)

    def get_message(self, message_id: str) -> GmailMessageMetadata:
        payload = self._get(f"messages/{message_id}", {"format": "metadata", "metadataHeaders": list(METADATA_HEADERS)})
        return parse_message_metadata(payload)

    def history(self, history_id: str, *, page_token: str | None = None) -> dict[str, Any]:
        params = {"startHistoryId": history_id}
        if page_token:
            params["pageToken"] = page_token
        return self._get("history", params)
