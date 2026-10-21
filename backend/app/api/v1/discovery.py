import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_id
from app.schemas.discovery import DiscoveryJobResult, DiscoveryMatchSummary, DiscoverySearchResponse
from app.services.discovery.search import search_discovered_jobs

router = APIRouter(prefix="/discovery", tags=["Discovery"])


@router.get("/jobs", response_model=DiscoverySearchResponse)
def list_discovered_jobs(
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    remote: str | None = None,
    status: str = Query("ACTIVE"),
    source_id: uuid.UUID | None = None,
    sort: str = Query("newest"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    search = search_discovered_jobs(
        db, user_id=user_id, query=q, category=category, location=location,
        remote=remote, status=status, source_id=source_id, sort=sort,
        limit=limit, offset=offset,
    )
    items = []
    for result in search.items:
        job = result["job"]
        match = result["match"]
        items.append(DiscoveryJobResult(
            id=job.id,
            company_name=job.company_name,
            job_title=job.job_title,
            location=job.location,
            source_url=job.source_url,
            availability_status=job.availability_status,
            work_arrangement=job.work_arrangement,
            location_restrictions=job.location_restrictions,
            already_saved=result["already_saved"],
            match=DiscoveryMatchSummary(
                score=match.score if match else None,
                ranking_status=match.ranking_status if match else "NEEDS_PROFILE",
                eligibility_status=match.eligibility_status if match else "UNKNOWN",
                matched_skills=list(match.matched_skills) if match else [],
                unverified_requirements=list(match.unverified_requirements) if match else [],
                explanations=list(match.explanations) if match else ["Create a confirmed candidate profile to calculate a match."],
            ),
        ))
    return DiscoverySearchResponse(items=items, total=search.total, limit=limit, offset=offset)
