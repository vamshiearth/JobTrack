import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_id
from app.models import DiscoverySource
from app.schemas.discovery import DiscoveryJobResult, DiscoveryMatchSummary, DiscoveryRefreshResponse, DiscoverySearchResponse, DiscoverySourceResponse
from app.schemas.job_opportunity import JobOpportunityCreate
from app.services.discovery.greenhouse import GreenhouseAdapter
from app.services.discovery.ingestion import ingest_greenhouse_board
from app.services.discovery.source_registry import GreenhouseBoard, GreenhouseBoardRegistry
from app.services.job_opportunities import create_opportunity
from app.services.discovery.search import search_discovered_jobs

router = APIRouter(prefix="/discovery", tags=["Discovery"])


@router.get("/sources", response_model=list[DiscoverySourceResponse])
def list_discovery_sources(user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return list(db.scalars(select(DiscoverySource).order_by(DiscoverySource.company_name)).all())


@router.post("/sources/{source_id}/refresh", response_model=DiscoveryRefreshResponse)
def refresh_discovery_source(source_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    source = db.get(DiscoverySource, source_id)
    if source is None or not source.enabled:
        raise HTTPException(status_code=404, detail="Discovery source not found")
    registry = GreenhouseBoardRegistry((GreenhouseBoard(source.board_token, source.company_name),))
    try:
        result = ingest_greenhouse_board(db, board_token=source.board_token, registry=registry, adapter=GreenhouseAdapter(registry))
        db.commit()
    except Exception as exc:
        db.rollback()
        source.last_error_code = type(exc).__name__[:50]
        db.commit()
        raise HTTPException(status_code=502, detail="Discovery refresh failed") from exc
    return DiscoveryRefreshResponse(source_id=source.id, **result.__dict__)


@router.post("/jobs/{job_id}/save")
def save_discovery_job(job_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    from app.models import DiscoveredJob
    job = db.get(DiscoveredJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Discovered job not found")
    opportunity, _ = create_opportunity(db, user_id=user_id, data=JobOpportunityCreate(
        company_name=job.company_name, job_title=job.job_title, location=job.location,
        work_arrangement=job.work_arrangement, description=job.description,
        source_job_id=job.provider_job_id, source_url=job.source_url,
    ))
    db.commit()
    return {"saved": True, "opportunity_id": opportunity.id}


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
