from collections.abc import Mapping
from time import sleep
from typing import Any, Protocol

import httpx

from app.schemas.discovered_opportunity import DiscoveredOpportunity
from app.services.discovery.normalization import sanitize_description, trusted_job_url
from app.services.discovery.source_registry import GreenhouseBoardRegistry


GREENHOUSE_API_HOST = "boards-api.greenhouse.io"


class DiscoveryError(RuntimeError):
    pass


class DiscoveryResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...

    def raise_for_status(self) -> None: ...


class DiscoveryClient(Protocol):
    def get(self, url: str, *, params: Mapping[str, object], timeout: float) -> DiscoveryResponse: ...


class GreenhouseAdapter:
    def __init__(
        self,
        registry: GreenhouseBoardRegistry,
        client: DiscoveryClient | None = None,
        *,
        timeout_seconds: float = 5.0,
        max_attempts: int = 2,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.registry = registry
        self.client = client or httpx.Client()
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts

    def fetch_jobs(self, board_token: str) -> list[DiscoveredOpportunity]:
        board = self.registry.resolve(board_token)
        url = f"https://{GREENHOUSE_API_HOST}/v1/boards/{board.token}/jobs"
        response = None
        for attempt in range(self.max_attempts):
            try:
                response = self.client.get(url, params={"content": "true"}, timeout=self.timeout_seconds)
                if response.status_code == 429 and attempt + 1 < self.max_attempts:
                    sleep(0.05)
                    continue
                response.raise_for_status()
                break
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                if attempt + 1 == self.max_attempts:
                    raise DiscoveryError("Greenhouse request failed") from exc
        if response is None:
            raise DiscoveryError("Greenhouse request failed")
        try:
            payload = response.json()
            jobs = payload["jobs"]
            if not isinstance(jobs, list):
                raise TypeError("jobs is not a list")
        except (KeyError, TypeError, ValueError) as exc:
            raise DiscoveryError("Greenhouse returned malformed JSON") from exc

        normalized: list[DiscoveredOpportunity] = []
        seen_ids: set[str] = set()
        for job in jobs:
            opportunity = self._normalize_job(job, board.token, board.company_name)
            if opportunity is not None and opportunity.source_job_id not in seen_ids:
                normalized.append(opportunity)
                seen_ids.add(opportunity.source_job_id)
        return normalized

    @staticmethod
    def _normalize_job(job: object, board_token: str, company_name: str) -> DiscoveredOpportunity | None:
        if not isinstance(job, dict):
            return None
        job_id = job.get("id")
        title = job.get("title")
        url = trusted_job_url(job.get("absolute_url"))
        if job_id is None or not str(job_id).strip() or not isinstance(title, str) or not title.strip() or url is None:
            return None
        location = job.get("location")
        location_name = location.get("name") if isinstance(location, dict) else None
        return DiscoveredOpportunity(
            source="GREENHOUSE",
            source_board=board_token,
            source_job_id=str(job_id),
            company_name=company_name,
            job_title=title.strip(),
            location=location_name.strip() if isinstance(location_name, str) and location_name.strip() else None,
            source_url=url,
            description=sanitize_description(job.get("content")),
        )
