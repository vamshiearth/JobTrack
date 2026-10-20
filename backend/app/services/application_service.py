from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import JobApplication
from app.schemas.application import ApplicationCreate, ApplicationUpdate


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


def update_application(
    db: Session,
    *,
    user_id: UUID,
    application_id: UUID,
    data: ApplicationUpdate,
) -> JobApplication | None:
    application = get_application(db, user_id=user_id, application_id=application_id)
    if application is None:
        return None

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field == "job_url" and value is not None:
            value = str(value)
        setattr(application, field, value)

    if changes:
        application.updated_at = datetime.now(timezone.utc)
        db.flush()
    return application


def delete_application(
    db: Session,
    *,
    user_id: UUID,
    application_id: UUID,
) -> bool:
    application = get_application(db, user_id=user_id, application_id=application_id)
    if application is None:
        return False
    db.delete(application)
    db.flush()
    return True