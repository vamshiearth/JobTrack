from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InitialSyncBatch:
    message_ids: tuple[str, ...]
    next_page_token: str | None


def select_initial_messages(response: dict[str, Any], *, remaining_limit: int) -> InitialSyncBatch:
    if not 1 <= remaining_limit <= 500:
        raise ValueError("Invalid remaining sync limit")
    raw_messages = response.get("messages", [])
    if not isinstance(raw_messages, list):
        raise ValueError("Invalid message list")
    ids: list[str] = []
    seen: set[str] = set()
    for message in raw_messages:
        if not isinstance(message, dict):
            continue
        message_id = message.get("id")
        if isinstance(message_id, str) and message_id and message_id not in seen:
            seen.add(message_id)
            ids.append(message_id)
            if len(ids) == remaining_limit:
                break
    page_token = response.get("nextPageToken")
    return InitialSyncBatch(tuple(ids), page_token if isinstance(page_token, str) else None)
