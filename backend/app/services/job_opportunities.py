from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import JobOpportunity
from app.schemas.job_opportunity import JobOpportunityCreate, JobOpportunityUpdate, OpportunityStatus


def normalize_url(value: str) -> str:
    normalized = value.strip()
    if normalized.endswith("/"):
        normalized = normalized[:-1]
    return normalized


def create_opportunity(db: Session, *, user_id: UUID, data: JobOpportunityCreate) -> tuple[JobOpportunity, bool]:
    normalized_url = normalize_url(str(data.source_url))
    opportunity = JobOpportunity(
        user_id=user_id,
        source_type=data.source_type.value,
        source_job_id=data.source_job_id,
        company_name=data.company_name,
        job_title=data.job_title,
        location=data.location,
        work_arrangement=data.work_arrangement.value if data.work_arrangement else None,
        employment_type=data.employment_type.value if data.employment_type else None,
        description=data.description,
        source_url=str(data.source_url),
        normalized_url=normalized_url,
        status=OpportunityStatus.SAVED.value,
    )
    savepoint = db.begin_nested()
    db.add(opportunity)
    try:
        db.flush()
        savepoint.commit()
        return opportunity, True
    except IntegrityError:
        savepoint.rollback()
        existing = db.scalar(select(JobOpportunity).where(JobOpportunity.user_id == user_id, JobOpportunity.normalized_url == normalized_url))
        if existing is None:
            raise
        return existing, False


def list_opportunities(db: Session, *, user_id: UUID, status: OpportunityStatus | None, page: int, page_size: int) -> tuple[list[JobOpportunity], int]:
    filters = [JobOpportunity.user_id == user_id]
    if status is not None:
        filters.append(JobOpportunity.status == status.value)
    total = db.scalar(select(func.count()).select_from(JobOpportunity).where(*filters)) or 0
    items = list(db.scalars(select(JobOpportunity).where(*filters).order_by(JobOpportunity.updated_at.desc(), JobOpportunity.id).offset((page - 1) * page_size).limit(page_size)).all())
    return items, total


def get_opportunity(db: Session, *, user_id: UUID, opportunity_id: UUID) -> JobOpportunity | None:
    return db.scalar(select(JobOpportunity).where(JobOpportunity.id == opportunity_id, JobOpportunity.user_id == user_id))


def update_opportunity(db: Session, *, user_id: UUID, opportunity_id: UUID, data: JobOpportunityUpdate) -> JobOpportunity | None:
    opportunity = get_opportunity(db, user_id=user_id, opportunity_id=opportunity_id)
    if opportunity is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(opportunity, field, value.value if hasattr(value, "value") else value)
    opportunity.updated_at = datetime.now(timezone.utc)
    db.flush()
    return opportunity
