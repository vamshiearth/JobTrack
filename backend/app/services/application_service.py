from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import JobApplication
from app.schemas.application import ApplicationCreate


def create_application(
    db: Session,
    *,
    user_id: UUID,
    data: ApplicationCreate,
) -> JobApplication:
    application = JobApplication(
        user_id=user_id,
        company_name=data.company_name,
        job_title=data.job_title,
        location=data.location,
        job_url=str(data.job_url) if data.job_url is not None else None,
        applied_at=data.applied_at,
        notes=data.notes,
        application_source="MANUAL",
        current_stage="APPLIED",
        next_action_owner="EMPLOYER",
        last_activity_at=datetime.now(timezone.utc),
    )
    db.add(application)
    db.flush()
    return application


def get_application(
    db: Session,
    *,
    user_id: UUID,
    application_id: UUID,
) -> JobApplication | None:
    return db.scalar(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == user_id,
        )
    )


def list_applications(
    db: Session,
    *,
    user_id: UUID,
) -> list[JobApplication]:
    return list(
        db.scalars(
            select(JobApplication)
            .where(JobApplication.user_id == user_id)
            .order_by(JobApplication.created_at.desc(), JobApplication.id)
        ).all()
    )


def count_applications(db: Session, *, user_id: UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(JobApplication).where(JobApplication.user_id == user_id)
    ) or 0