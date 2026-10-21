from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models import DiscoveredJob, DiscoverySource
from app.schemas.discovered_opportunity import DiscoveredOpportunity
from app.services.discovery.ingestion import _work_metadata, content_fingerprint
from app.services.discovery.normalization import trusted_job_url


QA_DATABASE = "jobtrack_step5_test"
QA_BOARD_TOKEN = "qa_fixture"
QA_FIXTURE_PREFIX = "qa-job-"

FIXTURES = (
    {
        "provider_job_id": "qa-job-001",
        "company_name": "Example Systems",
        "job_title": "Oracle CPQ Developer",
        "location": "United States",
        "description": "Synthetic QA fixture. Remote within the United States. Oracle CPQ development.",
    },
    {
        "provider_job_id": "qa-job-002",
        "company_name": "Demo Robotics",
        "job_title": "Java Backend Engineer",
        "location": "Boston, MA",
        "description": "Synthetic QA fixture. Hybrid Java and Spring Boot backend engineering.",
    },
    {
        "provider_job_id": "qa-job-003",
        "company_name": "Sample Analytics",
        "job_title": "Data Engineer",
        "location": "Boston, MA",
        "description": "Synthetic QA fixture. Onsite data engineering role.",
    },
    {
        "provider_job_id": "qa-job-004",
        "company_name": "Fictional Technologies",
        "job_title": "Associate Software Engineer",
        "location": None,
        "description": "Synthetic QA fixture. Arrangement and location intentionally unspecified.",
    },
    {
        "provider_job_id": "qa-job-005",
        "company_name": "Test Cloud Inc.",
        "job_title": "Python Backend Developer",
        "location": "Massachusetts",
        "description": "Synthetic QA fixture. Remote in Massachusetts. Python and FastAPI backend development.",
    },
)


def _opportunity(fixture: dict[str, str | None]) -> DiscoveredOpportunity:
    source_url = trusted_job_url(
        f"https://boards.greenhouse.io/{QA_BOARD_TOKEN}/jobs/{fixture['provider_job_id']}"
    )
    if source_url is None:
        raise ValueError("synthetic source URL failed validation")
    return DiscoveredOpportunity(
        source="GREENHOUSE",
        source_board=QA_BOARD_TOKEN,
        source_job_id=str(fixture["provider_job_id"]),
        company_name=str(fixture["company_name"]),
        job_title=str(fixture["job_title"]),
        location=fixture["location"],
        source_url=source_url,
        description=fixture["description"],
    )


def seed() -> None:
    if os.getenv("QA_SEED_ENABLED", "").lower() != "true":
        raise SystemExit("Refusing to seed: set QA_SEED_ENABLED=true explicitly")

    with SessionLocal() as db:
        database_name = db.scalar(text("SELECT current_database()"))
        if database_name != QA_DATABASE:
            raise SystemExit(f"Refusing to seed database {database_name!r}; expected {QA_DATABASE!r}")

        source = db.scalar(
            select(DiscoverySource).where(
                DiscoverySource.provider == "GREENHOUSE",
                DiscoverySource.board_token == QA_BOARD_TOKEN,
            )
        )
        if source is None:
            source = DiscoverySource(
                provider="GREENHOUSE",
                board_token=QA_BOARD_TOKEN,
                company_name="JobTrack Synthetic QA Fixtures",
                enabled=True,
            )
            db.add(source)
            db.flush()
        elif source.company_name != "JobTrack Synthetic QA Fixtures":
            raise SystemExit("Refusing to use an existing non-QA source with board token qa_fixture")

        now = datetime.now(timezone.utc)
        source.next_refresh_at = now + timedelta(days=365)
        for fixture in FIXTURES:
            opportunity = _opportunity(fixture)
            existing = db.scalar(
                select(DiscoveredJob).where(
                    DiscoveredJob.source_id == source.id,
                    DiscoveredJob.provider_job_id == opportunity.source_job_id,
                )
            )
            if existing is None:
                existing = DiscoveredJob(
                    source_id=source.id,
                    provider_job_id=opportunity.source_job_id,
                    first_seen_at=now,
                    created_at=now,
                )
                db.add(existing)
            elif not existing.provider_job_id.startswith(QA_FIXTURE_PREFIX):
                raise SystemExit("Refusing to overwrite a non-QA provider job")

            arrangement, restriction = _work_metadata(opportunity.location, opportunity.description)
            existing.company_name = opportunity.company_name
            existing.job_title = opportunity.job_title
            existing.location = opportunity.location
            existing.work_arrangement = arrangement
            existing.location_restrictions = restriction
            existing.description = opportunity.description
            existing.source_url = opportunity.source_url
            existing.content_fingerprint = content_fingerprint(opportunity)
            existing.last_seen_at = now
            existing.updated_at = now
            existing.availability_status = "ACTIVE"

        db.commit()
        print(f"Seeded {len(FIXTURES)} synthetic discovery jobs in {database_name}")


if __name__ == "__main__":
    seed()
