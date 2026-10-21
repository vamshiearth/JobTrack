from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApplicationEvent, JobApplication
from app.schemas.application_event import ApplicationEventCreate, EventKind
from app.services.event_rules import CLOSED_STAGES, get_status_for_event


class ApplicationNotFound(Exception):
    pass


class EventConflict(Exception):
    pass


def list_application_events(
    db: Session, *, user_id: UUID, application_id: UUID
) -> tuple[list[ApplicationEvent], int]:
    application = db.scalar(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == user_id,
        )
    )
    if application is None:
        raise ApplicationNotFound
    events = list(
        db.scalars(
            select(ApplicationEvent)
            .where(ApplicationEvent.job_application_id == application_id)
            .order_by(ApplicationEvent.occurred_at, ApplicationEvent.recorded_at)
        ).all()
    )
    return events, len(events)


def record_application_event(
    db: Session,
    *,
    user_id: UUID,
    application_id: UUID,
    data: ApplicationEventCreate,
    origin: str = "MANUAL",
    verified_by_user: bool = True,
    source_email_message_id: UUID | None = None,
) -> tuple[ApplicationEvent, bool]:
    application = db.scalar(
        select(JobApplication)
        .where(JobApplication.id == application_id, JobApplication.user_id == user_id)
        .with_for_update()
    )
    if application is None:
        raise ApplicationNotFound

    key = str(data.client_request_id)
    existing = db.scalar(
        select(ApplicationEvent).where(
            ApplicationEvent.job_application_id == application_id,
            ApplicationEvent.idempotency_key == key,
        )
    )
    if existing is not None:
        if (
            existing.event_kind != data.event_kind.value
            or existing.interview_round != data.interview_round
            or existing.details != data.details
            or existing.occurred_at != data.occurred_at.astimezone(timezone.utc)
        ):
            raise EventConflict("client_request_id was already used for another event")
        return existing, False

    if application.current_stage in CLOSED_STAGES:
        raise EventConflict("closed applications cannot receive ordinary events")
    if data.event_kind == EventKind.APPLICATION_SUBMITTED and origin == "MANUAL":
        raise EventConflict("application submission is recorded during application creation")

    prerequisite = {
        EventKind.ASSESSMENT_COMPLETED: EventKind.ASSESSMENT_INVITED,
        EventKind.INTERVIEW_COMPLETED: EventKind.INTERVIEW_SCHEDULED,
    }.get(data.event_kind)
    if prerequisite is not None:
        query = select(ApplicationEvent.id).where(
            ApplicationEvent.job_application_id == application_id,
            ApplicationEvent.event_kind == prerequisite.value,
        )
        if data.event_kind == EventKind.INTERVIEW_COMPLETED:
            query = query.where(ApplicationEvent.interview_round == data.interview_round)
        if db.scalar(query.limit(1)) is None:
            raise EventConflict("required prerequisite event was not found")

    stage, owner = get_status_for_event(data.event_kind)
    event = ApplicationEvent(
        job_application_id=application_id,
        source_email_message_id=source_email_message_id,
        event_kind=data.event_kind.value,
        interview_round=data.interview_round,
        origin=origin,
        verified_by_user=verified_by_user,
        details=data.details,
        idempotency_key=key,
        occurred_at=data.occurred_at.astimezone(timezone.utc),
    )
    db.add(event)
    if origin == "MANUAL" or data.occurred_at.astimezone(timezone.utc) >= application.last_activity_at:
        application.current_stage = stage
        application.next_action_owner = owner
        application.last_activity_at = data.occurred_at.astimezone(timezone.utc)
    application.updated_at = datetime.now(timezone.utc)
    db.flush()
    return event, True