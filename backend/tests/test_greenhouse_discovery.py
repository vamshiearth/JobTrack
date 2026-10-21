import httpx
import pytest

from app.services.discovery.greenhouse import DiscoveryError, GreenhouseAdapter
from app.services.discovery.source_registry import GreenhouseBoard, GreenhouseBoardRegistry, InvalidBoardToken


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("request failed", request=None, response=None)


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def adapter(client):
    registry = GreenhouseBoardRegistry((GreenhouseBoard("acme", "Acme Corp"),))
    return GreenhouseAdapter(registry, client, max_attempts=2)


def test_valid_jobs_are_normalized_and_duplicate_ids_collapsed():
    client = FakeClient([FakeResponse({"jobs": [
        {"id": 42, "title": "Engineer", "location": {"name": "Boston"}, "absolute_url": "https://boards.greenhouse.io/acme/jobs/42", "content": "<p>Build <b>things</b>.</p>"},
        {"id": 42, "title": "Duplicate", "absolute_url": "https://boards.greenhouse.io/acme/jobs/42"},
    ]})])

    result = adapter(client).fetch_jobs("acme")

    assert result[0].source == "GREENHOUSE"
    assert result[0].source_job_id == "42"
    assert result[0].company_name == "Acme Corp"
    assert result[0].description == "Build things."
    assert len(result) == 1
    assert client.calls[0][0] == "https://boards-api.greenhouse.io/v1/boards/acme/jobs"
    assert client.calls[0][1] == {"content": "true"}


def test_invalid_board_token_is_rejected_before_http_request():
    client = FakeClient([])
    with pytest.raises(InvalidBoardToken):
        adapter(client).fetch_jobs("unknown")
    assert client.calls == []


def test_missing_fields_and_unsafe_urls_are_skipped():
    client = FakeClient([FakeResponse({"jobs": [
        {"id": 1, "title": "No URL"},
        {"id": 2, "title": "Unsafe", "absolute_url": "javascript:alert(1)"},
        {"id": 3, "title": "Safe", "absolute_url": "https://example.com/jobs/3"},
    ]})])

    result = adapter(client).fetch_jobs("acme")
    assert [job.source_job_id for job in result] == ["3"]


def test_rate_limit_retries_once():
    client = FakeClient([FakeResponse({}, 429), FakeResponse({"jobs": []})])
    assert adapter(client).fetch_jobs("acme") == []
    assert len(client.calls) == 2


def test_timeout_is_a_controlled_failure_after_bounded_retry():
    client = FakeClient([httpx.ReadTimeout("timeout"), httpx.ReadTimeout("timeout")])
    with pytest.raises(DiscoveryError):
        adapter(client).fetch_jobs("acme")
    assert len(client.calls) == 2


def test_malformed_json_is_rejected_without_partial_results():
    client = FakeClient([FakeResponse({"unexpected": []})])
    with pytest.raises(DiscoveryError):
        adapter(client).fetch_jobs("acme")
