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


NON_RECRUITMENT_PATTERNS = (
    r"\b(one[ -]?time|verification|security)\s+code\b",
    r"\b(otp|2fa|mfa)\b",
    r"\bverify your (email|account|identity)\b",
    r"\bpassword reset\b",
    r"\bjob alerts?\b",
    r"\bnew jobs? for you\b",
    r"\brecommended jobs?\b",
    r"\bjobs? you might like\b",
    r"\bweekly (job|career) digest\b",
    r"\bnewsletter\b",
    r"\bunsubscribe\b",
    r"\bpromotional offer\b",
)

ACKNOWLEDGMENT_PATTERNS = (
    r"\bapplication (received|submitted|confirmed)\b",
    r"\bwe (have )?received your application\b",
    r"\bthank you for applying\b",
    r"\bthanks for applying\b",
    r"\byour application (has been|was) received\b",
    r"\bapplication confirmation\b",
    r"\bapplication is complete\b",
)

ASSESSMENT_PATTERNS = (
    r"\bassessment invitation\b",
    r"\bcomplete your (online |coding |technical )?assessment\b",
    r"\bcoding assessment\b",
    r"\bcoding challenge\b",
)

INTERVIEW_PATTERNS = (
    r"\binterview invitation\b",
    r"\bschedule (your |an )?interview\b",
    r"\bphone screen\b",
    r"\bschedule a call\b",
)

RECRUITER_CONTACT_PATTERNS = (
    r"\brecruiter (reaching out|is reaching out|contacted)\b",
    r"\blet's discuss your application\b",
    r"\b(?:i am|i'm|we are) reaching out about (?:your )?(?:application|position|role)\b",
    r"\bhiring team would like to speak\b",
    r"\bstill interested in (?:these )?jobs?\b",
)

OFFER_PATTERNS = (r"\bjob offer\b", r"\boffer letter\b", r"\boffer of employment\b", r"\bpleased to offer\b")
REJECTION_PATTERNS = (
    r"\bnot moving forward\b",
    r"\bregret to inform\b",
    r"\bapplication status update\b",
    r"\bnot selected\b",
    r"\bposition (?:has been )?filled\b",
)


def classify_recruitment_email(*, subject: str | None, sender: str | None) -> ClassificationResult:
    del sender
    text = normalize(subject)
    if any(re.search(pattern, text) for pattern in NON_RECRUITMENT_PATTERNS):
        return ClassificationResult(RecruitmentCategory.UNKNOWN, 0.0, ("Non-recruitment language detected",))

    rules = (
        (RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT, ACKNOWLEDGMENT_PATTERNS, 0.80, "Application acknowledgment language detected"),
        (RecruitmentCategory.ASSESSMENT_INVITATION, ASSESSMENT_PATTERNS, 0.86, "Assessment language detected"),
        (RecruitmentCategory.INTERVIEW_INVITATION, INTERVIEW_PATTERNS, 0.82, "Interview language detected"),
        (RecruitmentCategory.OFFER_POSSIBLE, OFFER_PATTERNS, 0.84, "Offer language detected"),
        (RecruitmentCategory.REJECTION_POSSIBLE, REJECTION_PATTERNS, 0.72, "Possible outcome language detected"),
        (RecruitmentCategory.RECRUITER_CONTACT, RECRUITER_CONTACT_PATTERNS, 0.66, "Recruiting contact language detected"),
    )
    for category, patterns, confidence, reason in rules:
        matched = tuple(pattern for pattern in patterns if re.search(pattern, text))
        if matched:
            return ClassificationResult(category, confidence, (reason, f"Matched: {', '.join(matched)}"))
    return ClassificationResult(RecruitmentCategory.UNKNOWN, 0.0, ("No supported recruitment pattern detected",))
