from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import DiscoveredJob, JobOpportunity
from app.services.job_matching import assess_match, get_profile
from app.services.job_opportunities import normalize_url


@dataclass(frozen=True)
class DiscoverySearch:
    items: list[dict]
    total: int


def search_discovered_jobs(
    db: Session,
    *,
    user_id: UUID,
    query: str | None = None,
    category: str | None = None,
    location: str | None = None,
    remote: str | None = None,
    status: str = "ACTIVE",
    source_id: UUID | None = None,
    sort: str = "newest",
    limit: int = 20,
    offset: int = 0,
) -> DiscoverySearch:
    predicates = []
    if query:
        term = f"%{query}%"
        predicates.append(or_(DiscoveredJob.company_name.ilike(term), DiscoveredJob.job_title.ilike(term)))
    category_terms = {
        "CPQ": ["cpq"],
        "JAVA_BACKEND": ["java", "spring", "backend"],
        "PYTHON_BACKEND": ["python", "fastapi"],
        "GENERAL_SWE": ["software engineer", "software developer", "full-stack"],
    }.get((category or "").upper())
    if category_terms:
        predicates.append(or_(*(DiscoveredJob.job_title.ilike(f"%{term}%") for term in category_terms)))
    if location:
        predicates.append(DiscoveredJob.location.ilike(f"%{location}%"))
    if remote:
        predicates.append(DiscoveredJob.work_arrangement == remote.upper())
    if status:
        predicates.append(DiscoveredJob.availability_status == status.upper())
    if source_id:
        predicates.append(DiscoveredJob.source_id == source_id)

    base = select(DiscoveredJob).where(*predicates)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    if sort == "title":
        base = base.order_by(DiscoveredJob.job_title.asc(), DiscoveredJob.id.asc())
    else:
        base = base.order_by(DiscoveredJob.last_seen_at.desc(), DiscoveredJob.id.asc())
    jobs = list(db.scalars(base).all())
    profile = get_profile(db, user_id=user_id)
    saved_urls = set(db.scalars(select(JobOpportunity.normalized_url).where(JobOpportunity.user_id == user_id)).all())
    results = []
    for job in jobs:
        match = assess_match(profile, job) if profile else None
        results.append({"job": job, "match": match, "already_saved": normalize_url(job.source_url) in saved_urls})
    if sort == "match_score":
        results.sort(key=lambda item: (item["match"].score if item["match"] and item["match"].score is not None else -1, str(item["job"].id)), reverse=True)
    return DiscoverySearch(results[offset : offset + limit], total)
