import re
from dataclasses import dataclass
from enum import StrEnum


class RecruitmentCategory(StrEnum):
    APPLICATION_ACKNOWLEDGMENT = "APPLICATION_ACKNOWLEDGMENT"
    RECRUITER_CONTACT = "RECRUITER_CONTACT"
    ASSESSMENT_INVITATION = "ASSESSMENT_INVITATION"
    INTERVIEW_INVITATION = "INTERVIEW_INVITATION"
    OFFER_POSSIBLE = "OFFER_POSSIBLE"
    REJECTION_POSSIBLE = "REJECTION_POSSIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ClassificationResult:
    category: RecruitmentCategory
    confidence: float
    reasons: tuple[str, ...]
    requires_review: bool = True


def normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").casefold().strip())


_PATTERNS: tuple[tuple[RecruitmentCategory, tuple[str, ...], float, str], ...] = (
    (RecruitmentCategory.ASSESSMENT_INVITATION, ("assessment", "coding challenge", "complete the test"), 0.86, "Assessment language detected"),
    (RecruitmentCategory.INTERVIEW_INVITATION, ("interview", "phone screen", "schedule a call"), 0.82, "Interview language detected"),
    (RecruitmentCategory.OFFER_POSSIBLE, ("job offer", "offer letter", "pleased to offer"), 0.84, "Offer language detected"),
    (RecruitmentCategory.REJECTION_POSSIBLE, ("not moving forward", "regret to inform", "application status update"), 0.72, "Possible outcome language detected"),
    (RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT, ("application received", "thanks for applying", "application confirmation"), 0.80, "Application acknowledgment language detected"),
    (RecruitmentCategory.RECRUITER_CONTACT, ("recruiter", "talent acquisition", "hiring team"), 0.66, "Recruiting contact language detected"),
)


def classify_recruitment_email(*, subject: str | None, sender: str | None) -> ClassificationResult:
    text = f"{normalize(subject)} {normalize(sender)}"
    for category, phrases, confidence, reason in _PATTERNS:
        matched = tuple(phrase for phrase in phrases if phrase in text)
        if matched:
            return ClassificationResult(category, confidence, (reason, f"Matched: {', '.join(matched)}"))
    return ClassificationResult(RecruitmentCategory.UNKNOWN, 0.0, ("No supported recruitment pattern detected",))
