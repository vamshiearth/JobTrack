from dataclasses import dataclass
from uuid import UUID

from app.services.application_matcher import ApplicationMatch
from app.services.recruitment_classifier import ClassificationResult, RecruitmentCategory


@dataclass(frozen=True)
class RecruitmentProposal:
    category: RecruitmentCategory
    application_id: UUID | None
    proposed_event_type: str | None
    confidence: float
    requires_review: bool
    reasons: tuple[str, ...]


EVENT_MAPPING = {
    RecruitmentCategory.RECRUITER_CONTACT: "RECRUITER_CONTACTED",
    RecruitmentCategory.ASSESSMENT_INVITATION: "ASSESSMENT_INVITED",
    RecruitmentCategory.INTERVIEW_INVITATION: "INTERVIEW_SCHEDULED",
    RecruitmentCategory.OFFER_POSSIBLE: "OFFER_RECEIVED",
    RecruitmentCategory.REJECTION_POSSIBLE: "REJECTION_RECEIVED",
}


def build_recruitment_proposal(classification: ClassificationResult, match: ApplicationMatch) -> RecruitmentProposal | None:
    if classification.category == RecruitmentCategory.UNKNOWN:
        return None
    reasons = classification.reasons + match.reasons
    if match.ambiguous:
        reasons += ("Application match requires manual selection",)
    application_id = None if match.ambiguous else match.application_id
    event_type = None if match.ambiguous else EVENT_MAPPING.get(classification.category)
    confidence = classification.confidence * match.confidence if application_id else classification.confidence
    return RecruitmentProposal(classification.category, application_id, event_type, confidence, True, reasons)
