from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApplicationHandoff, ApplicationPreparation, ApplicationSubmissionConfirmation
from app.schemas.application import ApplicationCreate
from app.schemas.application_handoff import SubmissionConfirmationRequest
from app.services.application_preparation import _current_source, _fingerprint
from app.services.application_service import create_application_with_submission_event


class HandoffConflict(Exception):
    pass


def create_handoff(db: Session, *, user_id: UUID, preparation_id: UUID) -> ApplicationHandoff | None:
    preparation = db.scalar(
        select(ApplicationPreparation).where(
            ApplicationPreparation.id == preparation_id,
            ApplicationPreparation.user_id == user_id,
        )
    )
    if preparation is None:
        return None
    source = _current_source(db, preparation=preparation)
    if preparation.status != "APPROVED" or preparation.approved_revision != preparation.draft_revision or source is None:
        raise HandoffConflict("preparation is not currently approved")
    if preparation.source_fingerprint != _fingerprint(*source):
        raise HandoffConflict("preparation is stale")
    handoff = ApplicationHandoff(
        user_id=user_id,
        preparation_id=preparation.id,
        approved_revision=preparation.draft_revision,
        source_url_snapshot=source[1].source_url,
        opened_at=datetime.now(timezone.utc),
    )
    db.add(handoff)
    db.flush()
    return handoff


def confirm_submission(
    db: Session, *, user_id: UUID, preparation_id: UUID, data: SubmissionConfirmationRequest
) -> ApplicationSubmissionConfirmation:
    preparation = db.scalar(
        select(ApplicationPreparation)
        .where(ApplicationPreparation.id == preparation_id, ApplicationPreparation.user_id == user_id)
        .with_for_update()
    )
    if preparation is None:
        raise LookupError("preparation not found")
    existing_key = db.scalar(select(ApplicationSubmissionConfirmation).where(ApplicationSubmissionConfirmation.idempotency_key == data.idempotency_key))
    if existing_key is not None:
        if existing_key.preparation_id != preparation_id or existing_key.user_id != user_id:
            raise HandoffConflict("idempotency key is already used")
        return existing_key
    if not data.user_confirmed_submission:
        raise HandoffConflict("explicit submission confirmation is required")
    if preparation.status != "APPROVED" or preparation.approved_revision != data.expected_revision or preparation.draft_revision != data.expected_revision:
        raise HandoffConflict("approval revision is stale")
    source = _current_source(db, preparation=preparation)
    if source is None or preparation.source_fingerprint != _fingerprint(*source):
        raise HandoffConflict("preparation is stale")
    if any(item.get("status") == "NEEDS_USER_INPUT" or item.get("answer") is None for item in preparation.application_answers):
        raise HandoffConflict("all application questions require explicit answers")
    if data.handoff_id is not None:
        handoff = db.scalar(
            select(ApplicationHandoff).where(
                ApplicationHandoff.id == data.handoff_id,
                ApplicationHandoff.user_id == user_id,
                ApplicationHandoff.preparation_id == preparation_id,
                ApplicationHandoff.approved_revision == data.expected_revision,
            )
        )
        if handoff is None:
            raise HandoffConflict("handoff not found for this preparation")
    if db.scalar(select(ApplicationSubmissionConfirmation).where(ApplicationSubmissionConfirmation.preparation_id == preparation_id)):
        raise HandoffConflict("submission already confirmed")
    opportunity = source[1]
    application = create_application_with_submission_event(
        db,
        user_id=user_id,
        data=ApplicationCreate(
            company_name=opportunity.company_name,
            job_title=opportunity.job_title,
            location=opportunity.location,
            job_url=opportunity.source_url,
            notes=f"Submitted from approved preparation {preparation.id}",
        ),
    )
    confirmation = ApplicationSubmissionConfirmation(
        user_id=user_id,
        preparation_id=preparation.id,
        handoff_id=data.handoff_id,
        job_application_id=application.id,
        confirmation_method="USER_ATTESTED",
        employer_confirmation_reference=data.employer_confirmation_reference,
        confirmed_at=datetime.now(timezone.utc),
        idempotency_key=data.idempotency_key,
    )
    db.add(confirmation)
    db.flush()
    return confirmation