from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models import DiscoverySource
from app.services.discovery import scheduler


def settings(enabled: bool = True):
    return SimpleNamespace(
        discovery_scheduler_enabled=enabled,
        discovery_refresh_interval_hours=6,
        discovery_lease_minutes=15,
        discovery_max_parallel=2,
    )


def test_scheduler_disabled_makes_no_claim(monkeypatch):
    monkeypatch.setattr(scheduler, "get_settings", lambda: settings(False))
    assert scheduler.run_scheduler_once().claimed == 0


def test_source_lease_allows_one_owner_and_recovers_after_expiry(monkeypatch):
    monkeypatch.setattr(scheduler, "get_settings", lambda: settings(True))
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        source = DiscoverySource(provider="GREENHOUSE", board_token="lease-test", company_name="Lease Test")
        db.add(source)
        db.commit()
        source_id = source.id
        first = scheduler.claim_due_source(now=now)
        second = scheduler.claim_due_source(now=now)
        assert first is not None
        assert second is None
        expired = now + timedelta(minutes=16)
        recovered = scheduler.claim_due_source(now=expired)
        assert recovered is not None
        assert recovered[0].id == source_id
        db.execute(delete(DiscoverySource).where(DiscoverySource.id == source_id))
        db.commit()


def test_expired_owner_cannot_complete_newer_lease(monkeypatch):
    monkeypatch.setattr(scheduler, "get_settings", lambda: settings(True))
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        source = DiscoverySource(provider="GREENHOUSE", board_token="lease-stale", company_name="Lease Stale")
        db.add(source)
        db.commit()
        first = scheduler.claim_due_source(now=now)
        second = scheduler.claim_due_source(now=now + timedelta(minutes=16))
        assert first is not None and second is not None
        assert scheduler.refresh_claimed_source(source.id, first[1], now=now + timedelta(minutes=16)) is False
        db.execute(delete(DiscoverySource).where(DiscoverySource.id == source.id))
        db.commit()
