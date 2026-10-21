import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CandidateProfile, JobMatchAssessment, JobOpportunity
from app.schemas.candidate_profile import CandidateProfileUpsert

SCORING_MODEL_VERSION = "v1"
SKILL_ALIASES = {
    "java": {"java"},
    "spring_boot": {"spring boot", "springboot"},
    "python": {"python"},
    "fastapi": {"fastapi", "fast api"},
    "react": {"react", "react.js", "reactjs"},
    "typescript": {"typescript"},
    "postgresql": {"postgresql", "postgres", "postgres db"},
    "oracle_cpq": {"oracle cpq", "oracle cpq cloud"},
    "sql": {"sql"},
    "docker": {"docker"},
}


@dataclass(frozen=True)
class JobMatchResult:
    score: int | None
    evidence_coverage: float
    matched_skills: tuple[str, ...]
    unverified_requirements: tuple[str, ...]
    explanations: tuple[str, ...]
    eligibility_status: str
    ranking_status: str


def normalize_skill(skill: str) -> str | None:
    value = re.sub(r"\s+", " ", skill.casefold().strip())
    for canonical, aliases in SKILL_ALIASES.items():
        if value in aliases:
            return canonical
    return None


def canonical_skills(confirmed_skills: list[str]) -> set[str]:
    return {canonical for skill in confirmed_skills if (canonical := normalize_skill(skill))}


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text.casefold()) is not None


def assess_match(profile: CandidateProfile, opportunity: JobOpportunity) -> JobMatchResult:
    text = " ".join(filter(None, [opportunity.job_title, opportunity.description])).casefold()
    profile_skills = canonical_skills(profile.skills)
    mentioned = tuple(sorted(canonical for canonical, aliases in SKILL_ALIASES.items() if any(_contains_phrase(text, alias) for alias in aliases)))
    matched = tuple(skill for skill in mentioned if skill in profile_skills)
    unverified = tuple(skill for skill in mentioned if skill not in profile_skills)
    explanations: list[str] = []

    if not opportunity.description:
        explanations.append("The opportunity has no description, so technical evidence is insufficient.")
    if matched:
        explanations.append("Confirmed profile evidence matches: " + ", ".join(matched) + ".")
    if unverified:
        explanations.append("Mentioned requirements not established by the profile: " + ", ".join(unverified) + ".")

    role_match = any(_contains_phrase(opportunity.job_title, role) for role in profile.target_roles if role.strip())
    location_match = any(_contains_phrase(opportunity.location or "", location) for location in profile.preferred_locations if location.strip())
    remote_match = profile.remote_preference and opportunity.work_arrangement == profile.remote_preference
    if role_match:
        explanations.append("The title aligns with a confirmed target role.")
    if location_match or remote_match:
        explanations.append("The location or work arrangement matches a stated preference.")
    elif profile.preferred_locations or profile.remote_preference:
        explanations.append("The opportunity does not match the stated location or work arrangement preference.")

    eligibility_unknown = any(term in text for term in ("work authorization", "sponsorship", "security clearance", "clearance required"))
    eligibility_status = "NEEDS_REVIEW" if eligibility_unknown else "UNKNOWN"
    if eligibility_unknown:
        explanations.append("Eligibility language requires user verification; it was not inferred from the profile.")

    if not opportunity.description or not mentioned:
        return JobMatchResult(None, 0.0, matched, unverified, tuple(explanations), eligibility_status, "INSUFFICIENT_EVIDENCE")

    skill_score = len(matched) / len(mentioned) * 40 if mentioned else 0
    role_score = 25 if role_match else 0
    preference_score = 15 if (location_match or remote_match) else 0
    experience_score = 20 if profile.experience_summary and any(skill in profile.experience_summary.casefold() for skill in matched) else 0
    score = round(skill_score + role_score + experience_score + preference_score)
    return JobMatchResult(score, len(matched) / len(mentioned), matched, unverified, tuple(explanations), eligibility_status, "NEEDS_REVIEW" if eligibility_unknown else "RANKED")


def get_profile(db: Session, *, user_id: UUID) -> CandidateProfile | None:
    return db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))


def upsert_profile(db: Session, *, user_id: UUID, data: CandidateProfileUpsert) -> CandidateProfile:
    profile = get_profile(db, user_id=user_id)
    values = data.model_dump()
    if profile is None:
        profile = CandidateProfile(user_id=user_id, revision=1, **values)
        db.add(profile)
    else:
        changed = any(getattr(profile, field) != value for field, value in values.items())
        for field, value in values.items():
            setattr(profile, field, value)
        if changed:
            profile.revision += 1
            profile.updated_at = datetime.now(timezone.utc)
    db.flush()
    return profile


def create_or_refresh_match(db: Session, *, user_id: UUID, opportunity_id: UUID) -> JobMatchAssessment | None:
    opportunity = db.scalar(select(JobOpportunity).where(JobOpportunity.id == opportunity_id, JobOpportunity.user_id == user_id))
    profile = get_profile(db, user_id=user_id)
    if opportunity is None or profile is None:
        return None
    result = assess_match(profile, opportunity)
    existing = db.scalar(select(JobMatchAssessment).where(JobMatchAssessment.opportunity_id == opportunity.id, JobMatchAssessment.candidate_profile_id == profile.id, JobMatchAssessment.profile_revision == profile.revision))
    if existing is not None and existing.opportunity_updated_at == opportunity.updated_at:
        return existing
    assessment = JobMatchAssessment(
        opportunity_id=opportunity.id, candidate_profile_id=profile.id, profile_revision=profile.revision,
        opportunity_updated_at=opportunity.updated_at, scoring_model_version=SCORING_MODEL_VERSION,
        score=result.score, evidence_coverage=Decimal(str(result.evidence_coverage)), matched_skills=list(result.matched_skills),
        unverified_requirements=list(result.unverified_requirements), explanations=list(result.explanations),
        eligibility_status=result.eligibility_status, ranking_status=result.ranking_status,
    )
    db.add(assessment)
    db.flush()
    return assessment


def get_current_match(db: Session, *, user_id: UUID, opportunity_id: UUID) -> JobMatchAssessment | None:
    assessment = db.scalar(select(JobMatchAssessment).join(JobOpportunity).where(JobOpportunity.id == opportunity_id, JobOpportunity.user_id == user_id).order_by(JobMatchAssessment.created_at.desc()))
    if assessment is None:
        return None
    profile = get_profile(db, user_id=user_id)
    opportunity = db.scalar(select(JobOpportunity).where(JobOpportunity.id == opportunity_id, JobOpportunity.user_id == user_id))
    if profile is None or opportunity is None or assessment.profile_revision != profile.revision or assessment.opportunity_updated_at != opportunity.updated_at:
        return None
    return assessment
