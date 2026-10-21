import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApplicationEvent, EmailMessage, JobApplication, ReviewItem
from app.services.application_matcher import ApplicationCandidate, match_application, sender_domain
from app.services.application_event_service import EventConflict, record_application_event
from app.services.recruitment_classifier import (
    RecruitmentCategory,
    classify_recruitment_email,
)
from app.schemas.application_event import ApplicationEventCreate, EventKind


@dataclass(frozen=True)
class GmailApplicationTrackerResult:
    scanned: int
    applications_added: int
    applications_matched: int
    needs_review: int
    status_changes: int = 0


@dataclass(frozen=True)
class ApplicationEvidence:
    company_name: str | None
    job_title: str | None


# These formats are deliberately conservative because Gmail metadata does not include bodies.
SUBJECT_PATTERNS = (
    re.compile(r"^(?:thank you for applying to|application (?:received|confirmed) for)\s+(.+?)\s+(?:-|\u2013|\u2014|at)\s+(.+)$", re.I),
    re.compile(r"^application received:\s*(.+?)\s+at\s+(.+)$", re.I),
    re.compile(r"^your application for\s+(.+?)\s+at\s+(.+?)\s+(?:has been|was) received", re.I),
    re.compile(r"^(?:application received|thank you for applying)\s*[-:]\s*(.+?)\s+at\s+(.+)$", re.I),
)
GENERIC_DOMAINS = {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "example.com", "example.org", "example.net"}


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -:|\t")


def _subject_evidence(subject: str | None) -> ApplicationEvidence:
    value = _clean(subject or "")
    for pattern in SUBJECT_PATTERNS:
        match = pattern.search(value)
        if match:
            first, second = (_clean(part) for part in match.groups())
            # The first format is role-at-company; the second is explicit role at company.
            return ApplicationEvidence(company_name=second, job_title=first)
    return ApplicationEvidence(None, None)


def extract_application_evidence(*, subject: str | None, sender: str | None) -> ApplicationEvidence:
    evidence = _subject_evidence(subject)
    if evidence.company_name and evidence.job_title:
        return evidence
    domain = sender_domain(sender)
    company = None
    if domain and domain not in GENERIC_DOMAINS and "." in domain:
        company = domain.split(".")[0].replace("-", " ").title()
    return ApplicationEvidence(company_name=company, job_title=evidence.job_title)


def _create_review(
    db: Session,
    *,
    user_id: UUID,
    message: EmailMessage,
    reason: str,
    category: RecruitmentCategory = RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT,
) -> bool:
    existing = db.scalar(select(ReviewItem).where(ReviewItem.email_message_id == message.id).with_for_update())
    if existing is not None:
        return False
    db.add(
        ReviewItem(
            user_id=user_id,
            email_message_id=message.id,
            confidence=0.80,
            reason=reason,
            review_status="PENDING",
        )
    )
    message.classification_kind = category.value
    message.processing_status = "REVIEW"
    return True


STATUS_EVENTS = {
    RecruitmentCategory.ASSESSMENT_INVITATION: EventKind.ASSESSMENT_INVITED,
    RecruitmentCategory.INTERVIEW_INVITATION: EventKind.INTERVIEW_SCHEDULED,
    RecruitmentCategory.OFFER_POSSIBLE: EventKind.OFFER_RECEIVED,
    RecruitmentCategory.REJECTION_POSSIBLE: EventKind.REJECTION_RECEIVED,
}


def _track_status_message(
    db: Session,
    *,
    user_id: UUID,
    message: EmailMessage,
    applications: list[JobApplication],
) -> tuple[bool, bool]:
    event_kind = STATUS_EVENTS.get(
        classify_recruitment_email(subject=message.subject, sender=message.sender_address).category
    )
    if event_kind is None or message.job_application_id is not None:
        return False, False
    candidates = [ApplicationCandidate(item.id, item.company_name, item.job_title) for item in applications]
    match = match_application(subject=message.subject, sender=message.sender_address, candidates=candidates)
    if match.application_id is None or match.ambiguous:
        return False, _create_review(
            db,
            user_id=user_id,
            message=message,
            reason="Status email could not be matched to one application",
            category=classify_recruitment_email(
                subject=message.subject, sender=message.sender_address
            ).category,
        )
    application = next(item for item in applications if item.id == match.application_id)
    try:
        record_application_event(
            db,
            user_id=user_id,
            application_id=application.id,
            source_email_message_id=message.id,
            origin="GMAIL",
            verified_by_user=False,
            data=ApplicationEventCreate(
                event_kind=event_kind,
                occurred_at=message.received_at,
                client_request_id=message.id,
                interview_round=1 if event_kind == EventKind.INTERVIEW_SCHEDULED else None,
                details={"evidence": "Gmail subject and sender metadata", "classification": event_kind.value},
            ),
        )
    except EventConflict:
        return False, _create_review(
            db,
            user_id=user_id,
            message=message,
            reason="Status email conflicts with the application history",
            category=classify_recruitment_email(
                subject=message.subject, sender=message.sender_address
            ).category,
        )
    message.job_application_id = application.id
    message.classification_kind = event_kind.value
    message.processing_status = "PROCESSED"
    message.processed_at = datetime.now(timezone.utc)
    return True, False


def track_application_confirmations(db: Session, *, user_id: UUID, connection_id: UUID) -> GmailApplicationTrackerResult:
    messages = list(
        db.scalars(
            select(EmailMessage)
            .where(EmailMessage.gmail_connection_id == connection_id)
            .order_by(EmailMessage.received_at, EmailMessage.id)
            .with_for_update()
        ).all()
    )
    applications = list(db.scalars(select(JobApplication).where(JobApplication.user_id == user_id)).all())
    candidates = [ApplicationCandidate(item.id, item.company_name, item.job_title) for item in applications]
    added = matched = needs_review = status_changes = 0

    for message in messages:
        classification = classify_recruitment_email(subject=message.subject, sender=message.sender_address)
        if classification.category != RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT:
            changed, reviewed = _track_status_message(
                db, user_id=user_id, message=message, applications=applications
            )
            status_changes += int(changed)
            needs_review += int(reviewed)
            continue
        if message.job_application_id is not None:
            continue
        evidence = extract_application_evidence(subject=message.subject, sender=message.sender_address)
        if not evidence.company_name or not evidence.job_title:
            needs_review += int(_create_review(db, user_id=user_id, message=message, reason="Application acknowledgment lacks reliable company or job title evidence"))
            continue

        match = match_application(subject=message.subject, sender=message.sender_address, candidates=candidates)
        if match.ambiguous:
            needs_review += int(_create_review(db, user_id=user_id, message=message, reason="Multiple existing applications could match this acknowledgment"))
            continue
        application = next((item for item in applications if item.id == match.application_id), None)
        if application is None:
            application = JobApplication(
                user_id=user_id,
                company_name=evidence.company_name,
                job_title=evidence.job_title,
                applied_at=message.received_at.date(),
                application_source="EMAIL",
                current_stage="APPLIED",
                next_action_owner="EMPLOYER",
                last_activity_at=message.received_at,
            )
            db.add(application)
            db.flush()
            applications.append(application)
            candidates.append(ApplicationCandidate(application.id, application.company_name, application.job_title))
            added += 1
        else:
            matched += 1
            if application.current_stage == "APPLIED" and message.received_at > application.last_activity_at:
                application.last_activity_at = message.received_at

        event_key = f"gmail-application-submitted-{message.gmail_connection_id}-{message.gmail_message_id}"
        event = db.scalar(select(ApplicationEvent).where(ApplicationEvent.job_application_id == application.id, ApplicationEvent.idempotency_key == event_key))
        if event is None:
            db.add(
                ApplicationEvent(
                    job_application_id=application.id,
                    source_email_message_id=message.id,
                    event_kind="APPLICATION_SUBMITTED",
                    origin="GMAIL",
                    verified_by_user=False,
                    idempotency_key=event_key,
                    occurred_at=message.received_at,
                    details={"evidence": "application acknowledgment"},
                )
            )
        message.job_application_id = application.id
        message.classification_kind = classification.category.value
        message.processing_status = "PROCESSED"
        message.processed_at = datetime.now(timezone.utc)

    db.commit()
    return GmailApplicationTrackerResult(len(messages), added, matched, needs_review, status_changes)
