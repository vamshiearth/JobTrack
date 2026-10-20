from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApplicationEvent, EmailMessage, GmailConnection, JobApplication, ReviewItem
from app.schemas.application_event import ApplicationEventCreate, EventKind
from app.services.application_event_service import ApplicationNotFound, EventConflict, record_application_event


class ReviewNotFound(Exception):
    pass


class ReviewConflict(Exception):
    pass


@dataclass(frozen=True)
class ReviewDecisionResult:
    review_id: UUID
    status: str
    application_id: UUID | None
    created_event_id: UUID | None


def review_idempotency_key(review_id: UUID) -> str:
    return str(UUID(int=review_id.int))


def approve_review(db: Session, *, review_id: UUID, user_id: UUID, application_id: UUID, interview_round: int | None) -> ReviewDecisionResult:
    review = db.scalar(select(ReviewItem).where(ReviewItem.id == review_id, ReviewItem.user_id == user_id).with_for_update())
    if review is None:
        raise ReviewNotFound
    if review.review_status != "PENDING":
        if review.review_status == "APPROVED" and review.suggested_application_id == application_id:
            event = db.scalar(select(ApplicationEvent).where(ApplicationEvent.idempotency_key == review_idempotency_key(review.id)))
            return ReviewDecisionResult(review.id, "APPROVED", application_id, event.id if event else None)
        raise ReviewConflict("review has already been decided")
    message = db.scalar(select(EmailMessage).join(GmailConnection).where(EmailMessage.id == review.email_message_id, GmailConnection.user_id == user_id))
    if message is None:
        raise ReviewNotFound
    application = db.scalar(select(JobApplication).where(JobApplication.id == application_id, JobApplication.user_id == user_id).with_for_update())
    if application is None:
        raise ApplicationNotFound
    if review.suggested_event_kind is None:
        raise ReviewConflict("this review has no event to approve")
    try:
        kind = EventKind(review.suggested_event_kind)
        data = ApplicationEventCreate(event_kind=kind, occurred_at=datetime.now(timezone.utc), client_request_id=UUID(int=review.id.int), interview_round=interview_round)
    except (ValueError, TypeError) as error:
        raise ReviewConflict("review event is not supported or is missing required details") from error
    try:
        event, _ = record_application_event(db, user_id=user_id, application_id=application_id, data=data)
    except EventConflict as error:
        raise ReviewConflict(str(error)) from error
    review.review_status = "APPROVED"
    review.suggested_application_id = application_id
    review.resolved_at = datetime.now(timezone.utc)
    db.flush()
    return ReviewDecisionResult(review.id, "APPROVED", application_id, event.id)


def reject_review(db: Session, *, review_id: UUID, user_id: UUID) -> ReviewDecisionResult:
    review = db.scalar(select(ReviewItem).where(ReviewItem.id == review_id, ReviewItem.user_id == user_id).with_for_update())
    if review is None:
        raise ReviewNotFound
    if review.review_status == "DISMISSED":
        return ReviewDecisionResult(review.id, "REJECTED", review.suggested_application_id, None)
    if review.review_status != "PENDING":
        raise ReviewConflict("review has already been decided")
    review.review_status = "DISMISSED"
    review.resolved_at = datetime.now(timezone.utc)
    db.flush()
    return ReviewDecisionResult(review.id, "REJECTED", review.suggested_application_id, None)