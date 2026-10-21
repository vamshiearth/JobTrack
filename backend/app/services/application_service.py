from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import ApplicationEvent, JobApplication
from app.schemas.application import (
    ApplicationCreate,
    ApplicationStage,
    ApplicationUpdate,
    NextActionOwner,
)


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

def create_application_with_submission_event(
    db: Session,
    *,
    user_id: UUID,
    data: ApplicationCreate,
    occurred_at: datetime | None = None,
) -> JobApplication:
    application = create_application(db, user_id=user_id, data=data)
    db.add(
        ApplicationEvent(
            job_application_id=application.id,
            event_kind="APPLICATION_SUBMITTED",
            origin="MANUAL",
            verified_by_user=True,
            idempotency_key=f"application-created-{application.id}",
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )
    )
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
    q: str | None = None,
    stage: ApplicationStage | None = None,
    next_action_owner: NextActionOwner | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "last_activity_at",
    sort_order: str = "desc",
) -> tuple[list[JobApplication], int]:
    filters = [JobApplication.user_id == user_id]
    if q is not None and q.strip():
        search_term = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{search_term}%"
        filters.append(
            or_(
                JobApplication.company_name.ilike(pattern, escape="\\"),
                JobApplication.job_title.ilike(pattern, escape="\\"),
            )
        )
    if stage is not None:
        filters.append(JobApplication.current_stage == stage.value)
    if next_action_owner is not None:
        filters.append(JobApplication.next_action_owner == next_action_owner.value)

    sort_column = {
        "last_activity_at": JobApplication.last_activity_at,
        "applied_at": JobApplication.applied_at,
        "company_name": JobApplication.company_name,
    }[sort_by]
    order_by = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    total = db.scalar(select(func.count()).select_from(JobApplication).where(*filters)) or 0
    offset = (page - 1) * page_size
    applications = list(
        db.scalars(
            select(JobApplication)
            .where(*filters)
            .order_by(order_by, JobApplication.id)
            .offset(offset)
            .limit(page_size)
        ).all()
    )
    return applications, total


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