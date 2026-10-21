import pytest
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models import DiscoveredJob, DiscoverySource
from app.schemas.discovered_opportunity import DiscoveredOpportunity
from app.services.discovery.greenhouse import DiscoveryError
from app.services.discovery.ingestion import ingest_greenhouse_board
from app.services.discovery.source_registry import GreenhouseBoard, GreenhouseBoardRegistry


class FakeAdapter:
    def __init__(self, jobs):
        self.jobs = jobs
        self.calls = 0

    def fetch_jobs(self, board_token):
        self.calls += 1
        return self.jobs


def job(title="Engineer", description="Build systems"):
    return DiscoveredOpportunity(
        source="GREENHOUSE",
        source_board="acme",
        source_job_id="42",
        company_name="Acme Corp",
        job_title=title,
        location="Boston",
        source_url="https://boards.greenhouse.io/acme/jobs/42",
        description=description,
    )


@pytest.fixture
def registry():
    return GreenhouseBoardRegistry((GreenhouseBoard("acme", "Acme Corp"),))


def test_ingestion_upserts_and_distinguishes_counts(registry):
    adapter = FakeAdapter([job()])
    with SessionLocal() as db:
        first = ingest_greenhouse_board(db, board_token="acme", registry=registry, adapter=adapter)
        db.commit()
        second = ingest_greenhouse_board(db, board_token="acme", registry=registry, adapter=adapter)
        db.commit()
        adapter.jobs = [job(title="Senior Engineer")]
        third = ingest_greenhouse_board(db, board_token="acme", registry=registry, adapter=adapter)
        db.commit()
        assert (first.created, first.updated, first.unchanged) == (1, 0, 0)
        assert (second.created, second.updated, second.unchanged) == (0, 0, 1)
        assert (third.created, third.updated, third.unchanged) == (0, 1, 0)
        assert db.scalar(select(DiscoverySource.last_success_at).where(DiscoverySource.board_token == "acme")) is not None
        assert db.scalar(select(DiscoveredJob.job_title).where(DiscoveredJob.provider_job_id == "42")) == "Senior Engineer"
        db.execute(delete(DiscoverySource).where(DiscoverySource.board_token == "acme"))
        db.commit()


def test_disabled_source_rejects_refresh(registry):
    with SessionLocal() as db:
        source = DiscoverySource(provider="GREENHOUSE", board_token="acme", company_name="Acme Corp", enabled=False)
        db.add(source)
        db.commit()
        with pytest.raises(ValueError, match="disabled"):
            ingest_greenhouse_board(db, board_token="acme", registry=registry, adapter=FakeAdapter([]))
        db.rollback()
        db.execute(delete(DiscoverySource).where(DiscoverySource.board_token == "acme"))
        db.commit()


def test_fetch_failure_does_not_mark_success(registry):
    with SessionLocal() as db:
        source = DiscoverySource(provider="GREENHOUSE", board_token="acme", company_name="Acme Corp", enabled=True)
        db.add(source)
        db.commit()
        class FailingAdapter:
            def fetch_jobs(self, board_token):
                raise DiscoveryError("network failure")
        with pytest.raises(DiscoveryError):
            ingest_greenhouse_board(db, board_token="acme", registry=registry, adapter=FailingAdapter())
        db.rollback()
        assert db.scalar(select(DiscoverySource.last_success_at).where(DiscoverySource.board_token == "acme")) is None
        db.execute(delete(DiscoverySource).where(DiscoverySource.board_token == "acme"))
        db.commit()
