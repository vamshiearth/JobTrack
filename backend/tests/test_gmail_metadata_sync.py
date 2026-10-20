import pytest

from app.services.gmail_history_planning import parse_history_page
from app.services.gmail_metadata_client import parse_message_metadata
from app.services.gmail_sync_planning import select_initial_messages


def test_metadata_extracts_allowed_headers():
    parsed = parse_message_metadata({"id": "gmail-001", "threadId": "thread-001", "historyId": "12345", "internalDate": "1760000000000", "labelIds": ["INBOX"], "payload": {"headers": [{"name": "From", "value": "jobs@example.com"}, {"name": "Subject", "value": "Interview invitation"}, {"name": "X-Internal", "value": "not stored"}]}})
    assert parsed.message_id == "gmail-001"
    assert parsed.headers["subject"] == "Interview invitation"
    assert "x-internal" not in parsed.headers


def test_metadata_rejects_invalid_identity():
    with pytest.raises(ValueError):
        parse_message_metadata({"id": "", "threadId": "thread"})


def test_initial_batch_deduplicates_and_obeys_limit():
    batch = select_initial_messages({"messages": [{"id": "a"}, {"id": "a"}, {"id": "b"}], "nextPageToken": "next"}, remaining_limit=2)
    assert batch.message_ids == ("a", "b")
    assert batch.next_page_token == "next"


def test_initial_batch_rejects_invalid_limit():
    with pytest.raises(ValueError):
        select_initial_messages({}, remaining_limit=0)


def test_history_collects_additions_labels_and_deletions():
    changes = parse_history_page({"historyId": "99", "history": [{"messagesAdded": [{"message": {"id": "a"}}], "labelsAdded": [{"message": {"id": "b"}}], "labelsRemoved": [{"message": {"id": "c"}}], "messagesDeleted": [{"message": {"id": "d"}}]}], "nextPageToken": "p"})
    assert changes.refresh_ids == frozenset({"a", "b", "c"})
    assert changes.deleted_ids == frozenset({"d"})
    assert changes.next_page_token == "p"
    assert changes.response_history_id == "99"


def test_history_deletion_supersedes_refresh_on_same_page():
    changes = parse_history_page({"history": [{"messagesAdded": [{"message": {"id": "a"}}], "messagesDeleted": [{"message": {"id": "a"}}]}]})
    assert changes.refresh_ids == frozenset()
    assert changes.deleted_ids == frozenset({"a"})


def test_history_rejects_malformed_changes():
    with pytest.raises(ValueError):
        parse_history_page({"history": [{"messagesAdded": {}}]})


def test_metadata_parses_numeric_internal_date_and_labels():
    parsed = parse_message_metadata({"id": "a", "threadId": "t", "internalDate": "10", "labelIds": ["INBOX", 4], "payload": {"headers": []}})
    assert parsed.internal_date_ms == 10
    assert parsed.labels == ("INBOX",)
