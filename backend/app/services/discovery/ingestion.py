from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DiscoveredJob, DiscoverySource
from app.schemas.discovered_opportunity import DiscoveredOpportunity
from app.services.discovery.greenhouse import GreenhouseAdapter
from app.services.discovery.source_registry import GreenhouseBoardRegistry, InvalidBoardToken


@dataclass(frozen=True)
class IngestionResult:
    created: int
    updated: int
    unchanged: int
    observed: int


def content_fingerprint(job: DiscoveredOpportunity) -> str:
    payload = {
        "company_name": job.company_name,
        "job_title": job.job_title,
        "location": job.location,
        "description": job.description,
        "source_url": job.source_url,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def ingest_greenhouse_board(
    db: Session,
    *,
    board_token: str,
    registry: GreenhouseBoardRegistry,
    adapter: GreenhouseAdapter,
) -> IngestionResult:
    board = registry.resolve(board_token)
    source = db.scalar(
        select(DiscoverySource)
        .where(DiscoverySource.provider == "GREENHOUSE", DiscoverySource.board_token == board.token)
        .with_for_update()
    )
    if source is None:
        source = DiscoverySource(
            provider="GREENHOUSE",
            board_token=board.token,
            company_name=board.company_name,
            enabled=True,
        )
        db.add(source)
        db.flush()
    if not source.enabled:
        raise ValueError("discovery source is disabled")
    jobs = adapter.fetch_jobs(board.token)
    now = datetime.now(timezone.utc)
    created = updated = unchanged = 0
    for job in jobs:
        fingerprint = content_fingerprint(job)
        existing = db.scalar(
            select(DiscoveredJob)
            .where(
                DiscoveredJob.source_id == source.id,
                DiscoveredJob.provider_job_id == job.source_job_id,
            )
            .with_for_update()
        )
        if existing is None:
            db.add(
                DiscoveredJob(
                    source_id=source.id,
                    provider_job_id=job.source_job_id,
                    company_name=job.company_name,
                    job_title=job.job_title,
                    location=job.location,
                    description=job.description,
                    source_url=job.source_url,
                    content_fingerprint=fingerprint,
                    first_seen_at=now,
                    last_seen_at=now,
                    availability_status="ACTIVE",
                )
            )
            created += 1
        else:
            changed = existing.content_fingerprint != fingerprint or existing.availability_status != "ACTIVE"
            existing.company_name = job.company_name
            existing.job_title = job.job_title
            existing.location = job.location
            existing.description = job.description
            existing.source_url = job.source_url
            existing.content_fingerprint = fingerprint
            existing.last_seen_at = now
            existing.availability_status = "ACTIVE"
            if changed:
                updated += 1
            else:
                unchanged += 1
    source.last_success_at = now
    source.last_error_code = None
    db.flush()
    return IngestionResult(created=created, updated=updated, unchanged=unchanged, observed=len(jobs))
