import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApplicationPreparation, CandidateProfile, JobMatchAssessment, JobOpportunity
from app.schemas.application_preparation import PreparationStatus, PreparationUpdate
from app.services.job_matching import get_current_match


def _fingerprint(profile: CandidateProfile, opportunity: JobOpportunity, match: JobMatchAssessment | None) -> str:
    source = {
        "profile_revision": profile.revision,
        "resume_version": profile.resume_version,
        "opportunity_updated_at": opportunity.updated_at.isoformat(),
        "match_id": str(match.id) if match else None,
    }
    return hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()[:32]


def _generate_content(profile: CandidateProfile, opportunity: JobOpportunity, match: JobMatchAssessment | None) -> tuple[list[dict], list[dict]]:
    matched = list(match.matched_skills) if match else []
    suggestions = [
        {
            "source_evidence_id": f"candidate_profile:{profile.id}:skills",
            "target_requirement": skill,
            "suggested_emphasis": f"Emphasize your confirmed {skill} experience where it is already documented.",
            "verification_required": False,
        }
        for skill in matched
    ]
    if profile.experience_summary:
        suggestions.append({
            "source_evidence_id": f"candidate_profile:{profile.id}:experience_summary",
            "target_requirement": opportunity.job_title,
            "suggested_emphasis": "Review and emphasize the relevant parts of your confirmed experience summary without changing dates or titles.",
            "verification_required": True,
        })
    answers = [
        {"question_key": "work_authorization", "answer": None, "status": "NEEDS_USER_INPUT"},
        {"question_key": "sponsorship", "answer": None, "status": "NEEDS_USER_INPUT"},
    ]
    return suggestions, answers


def _get_owned(db: Session, *, user_id: UUID, preparation_id: UUID) -> ApplicationPreparation | None:
    return db.scalar(select(ApplicationPreparation).where(ApplicationPreparation.id == preparation_id, ApplicationPreparation.user_id == user_id))


def _current_source(db: Session, preparation: ApplicationPreparation) -> tuple[CandidateProfile, JobOpportunity, JobMatchAssessment | None] | None:
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.id == preparation.candidate_profile_id, CandidateProfile.user_id == preparation.user_id))
    opportunity = db.scalar(select(JobOpportunity).where(JobOpportunity.id == preparation.opportunity_id, JobOpportunity.user_id == preparation.user_id))
    if profile is None or opportunity is None:
        return None
    match = get_current_match(db, user_id=preparation.user_id, opportunity_id=opportunity.id)
    return profile, opportunity, match


def create_preparation(db: Session, *, user_id: UUID, opportunity_id: UUID) -> ApplicationPreparation | None:
    opportunity = db.scalar(select(JobOpportunity).where(JobOpportunity.id == opportunity_id, JobOpportunity.user_id == user_id))
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    if opportunity is None or profile is None:
        return None
    match = get_current_match(db, user_id=user_id, opportunity_id=opportunity_id)
    suggestions, answers = _generate_content(profile, opportunity, match)
    fingerprint = _fingerprint(profile, opportunity, match)
    preparation = ApplicationPreparation(
        user_id=user_id, opportunity_id=opportunity.id, candidate_profile_id=profile.id,
        match_assessment_id=match.id if match else None, source_fingerprint=fingerprint,
        status=PreparationStatus.NEEDS_REVIEW.value, resume_suggestions=suggestions,
        application_answers=answers,
    )
    db.add(preparation)
    db.flush()
    return preparation


def get_preparation(db: Session, *, user_id: UUID, preparation_id: UUID) -> ApplicationPreparation | None:
    preparation = _get_owned(db, user_id=user_id, preparation_id=preparation_id)
    if preparation is None:
        return None
    current = _current_source(db, preparation)
    if current is None:
        return preparation
    profile, opportunity, match = current
    if preparation.source_fingerprint != _fingerprint(profile, opportunity, match) and preparation.status not in (PreparationStatus.ARCHIVED.value, PreparationStatus.STALE.value):
        preparation.status = PreparationStatus.STALE.value
        preparation.updated_at = datetime.now(timezone.utc)
        db.flush()
    return preparation


def update_preparation(db: Session, *, user_id: UUID, preparation_id: UUID, data: PreparationUpdate) -> ApplicationPreparation | None:
    preparation = _get_owned(db, user_id=user_id, preparation_id=preparation_id)
    if preparation is None:
        return None
    changes = data.model_dump(exclude_unset=True)
    requested_status = changes.pop("status", None)
    for field, value in changes.items():
        setattr(preparation, field, value)
    if changes:
        preparation.draft_revision += 1
        preparation.status = PreparationStatus.NEEDS_REVIEW.value
        preparation.approved_at = None
        preparation.approved_revision = None
    if requested_status is not None:
        if requested_status.value == PreparationStatus.APPROVED.value:
            current = get_preparation(db, user_id=user_id, preparation_id=preparation_id)
            if current is None or current.status == PreparationStatus.STALE.value:
                return None
            preparation.status = PreparationStatus.APPROVED.value
            preparation.approved_at = datetime.now(timezone.utc)
            preparation.approved_revision = preparation.draft_revision
        elif requested_status.value != PreparationStatus.APPROVED.value:
            preparation.status = requested_status.value
    preparation.updated_at = datetime.now(timezone.utc)
    db.flush()
    return preparation
