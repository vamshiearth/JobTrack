from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HistoryChanges:
    refresh_ids: frozenset[str]
    deleted_ids: frozenset[str]
    next_page_token: str | None
    response_history_id: str | None


def parse_history_page(payload: dict[str, Any]) -> HistoryChanges:
    records = payload.get("history", [])
    if not isinstance(records, list):
        raise ValueError("Invalid Gmail history records")
    refresh: set[str] = set()
    deleted: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid history record")
        for change_type in ("messagesAdded", "labelsAdded", "labelsRemoved"):
            changes = record.get(change_type, [])
            if not isinstance(changes, list):
                raise ValueError("Invalid Gmail changes")
            for change in changes:
                if not isinstance(change, dict):
                    raise ValueError("Invalid Gmail change")
                message = change.get("message", {})
                if isinstance(message, dict) and isinstance(message.get("id"), str) and message["id"]:
                    refresh.add(message["id"])
        changes = record.get("messagesDeleted", [])
        if not isinstance(changes, list):
            raise ValueError("Invalid Gmail changes")
        for change in changes:
            if not isinstance(change, dict):
                raise ValueError("Invalid Gmail change")
            message = change.get("message", {})
            if isinstance(message, dict) and isinstance(message.get("id"), str) and message["id"]:
                deleted.add(message["id"])
    refresh -= deleted
    return HistoryChanges(
        frozenset(refresh),
        frozenset(deleted),
        payload.get("nextPageToken") if isinstance(payload.get("nextPageToken"), str) else None,
        payload.get("historyId") if isinstance(payload.get("historyId"), str) else None,
    )
