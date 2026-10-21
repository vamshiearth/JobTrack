from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import or_, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import DiscoverySource
from app.services.discovery.greenhouse import DiscoveryError, GreenhouseAdapter
from app.services.discovery.ingestion import ingest_greenhouse_board
from app.services.discovery.source_registry import GreenhouseBoard, GreenhouseBoardRegistry


@dataclass(frozen=True)
class SchedulerRun:
    claimed: int
    succeeded: int
    failed: int
    skipped: int


def claim_due_source(*, now: datetime | None = None) -> tuple[DiscoverySource, str] | None:
    current = now or datetime.now(timezone.utc)
    settings = get_settings()
    with SessionLocal() as db:
        source = db.scalar(
            select(DiscoverySource)
            .where(
                DiscoverySource.enabled.is_(True),
                or_(DiscoverySource.next_refresh_at.is_(None), DiscoverySource.next_refresh_at <= current),
                or_(DiscoverySource.lease_expires_at.is_(None), DiscoverySource.lease_expires_at <= current),
            )
            .order_by(DiscoverySource.next_refresh_at.asc().nulls_first(), DiscoverySource.id)
            .with_for_update(skip_locked=True)
        )
        if source is None:
            return None
        token = uuid4().hex
        source.lease_token = token
        source.lease_expires_at = current + timedelta(minutes=settings.discovery_lease_minutes)
        source.last_refresh_status = "RUNNING"
        db.commit()
        db.refresh(source)
        return source, token


def refresh_claimed_source(source_id, lease_token: str, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    settings = get_settings()
    with SessionLocal() as db:
        source = db.scalar(select(DiscoverySource).where(DiscoverySource.id == source_id, DiscoverySource.lease_token == lease_token))
        if source is None or source.lease_expires_at is None or source.lease_expires_at <= current:
            return False
        registry = GreenhouseBoardRegistry((GreenhouseBoard(source.board_token, source.company_name),))
        try:
            result = ingest_greenhouse_board(db, board_token=source.board_token, registry=registry, adapter=GreenhouseAdapter(registry))
            completed = datetime.now(timezone.utc)
            source.last_refresh_status = "SUCCESS"
            source.last_error_code = None
            source.next_refresh_at = completed + timedelta(hours=settings.discovery_refresh_interval_hours)
            source.lease_token = None
            source.lease_expires_at = None
            db.commit()
            return result.observed >= 0
        except Exception as exc:
            db.rollback()
            source = db.scalar(select(DiscoverySource).where(DiscoverySource.id == source_id, DiscoverySource.lease_token == lease_token))
            if source is not None:
                source.last_refresh_status = "FAILED"
                source.last_error_code = type(exc).__name__[:50]
                source.next_refresh_at = current + timedelta(hours=settings.discovery_refresh_interval_hours)
                source.lease_token = None
                source.lease_expires_at = None
                db.commit()
            return False


def run_scheduler_once(*, now: datetime | None = None) -> SchedulerRun:
    settings = get_settings()
    if not settings.discovery_scheduler_enabled:
        return SchedulerRun(0, 0, 0, 0)
    claimed = succeeded = failed = skipped = 0
    for _ in range(settings.discovery_max_parallel):
        claim = claim_due_source(now=now)
        if claim is None:
            break
        source, lease_token = claim
        claimed += 1
        if refresh_claimed_source(source.id, lease_token, now=now):
            succeeded += 1
        else:
            failed += 1
    return SchedulerRun(claimed, succeeded, failed, skipped)


def scheduler_loop() -> None:
    import time

    settings = get_settings()
    while settings.discovery_scheduler_enabled:
        run_scheduler_once()
        time.sleep(settings.discovery_refresh_interval_hours * 3600)


if __name__ == "__main__":
    scheduler_loop()
