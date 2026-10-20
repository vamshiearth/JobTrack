from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmailMessage, GmailConnection, JobApplication, ReviewItem
from app.services.application_matcher import ApplicationCandidate, match_application
from app.services.recruitment_classifier import classify_recruitment_email
from app.services.recruitment_proposals import build_recruitment_proposal


class ClassificationNotEligible(Exception):
    pass


@dataclass(frozen=True)
class ClassificationBatchResult:
    scanned: int
    proposed: int
    skipped: int
    ambiguous: int


def classify_saved_messages(db: Session, *, user_id: UUID, connection_id: UUID) -> ClassificationBatchResult:
    connection = db.scalar(select(GmailConnection).where(GmailConnection.id == connection_id, GmailConnection.user_id == user_id))
    if connection is None or connection.connection_status != "CONNECTED":
        raise ClassificationNotEligible("Gmail connection is not eligible for classification")
    applications = list(db.scalars(select(JobApplication).where(JobApplication.user_id == user_id)))
    candidates = [ApplicationCandidate(application.id, application.company_name, application.job_title) for application in applications]
    messages = list(db.scalars(select(EmailMessage).join(GmailConnection).where(EmailMessage.gmail_connection_id == connection_id, GmailConnection.user_id == user_id)))
    proposed = skipped = ambiguous = 0
    for message in messages:
        classification = classify_recruitment_email(subject=message.subject, sender=message.sender_address)
        match = match_application(subject=message.subject, sender=message.sender_address, candidates=candidates)
        proposal = build_recruitment_proposal(classification, match)
        if proposal is None:
            skipped += 1
            continue
        if match.ambiguous:
            ambiguous += 1
        pending = db.scalar(select(ReviewItem).where(ReviewItem.email_message_id == message.id, ReviewItem.review_status == "PENDING").with_for_update())
        if pending is not None:
            skipped += 1
            continue
        db.add(ReviewItem(user_id=user_id, email_message_id=message.id, suggested_application_id=proposal.application_id, suggested_event_kind=proposal.proposed_event_type, confidence=Decimal(str(min(proposal.confidence, 0.999))), reason="; ".join(proposal.reasons), review_status="PENDING"))
        message.classification_kind = proposal.category.value
        proposed += 1
    db.commit()
    return ClassificationBatchResult(len(messages), proposed, skipped, ambiguous)
