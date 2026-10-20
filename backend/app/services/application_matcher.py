import re
from dataclasses import dataclass
from uuid import UUID

from app.services.recruitment_classifier import normalize

GENERIC_COMPANY_WORDS = {"company", "technologies", "technology", "solutions", "systems", "software", "services", "inc", "llc", "corp", "corporation", "group", "the", "example", "jobs", "mail", "email", "no", "reply"}


@dataclass(frozen=True)
class ApplicationCandidate:
    id: UUID
    company_name: str
    job_title: str


@dataclass(frozen=True)
class ApplicationMatch:
    application_id: UUID | None
    confidence: float
    reasons: tuple[str, ...]
    ambiguous: bool = False


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", normalize(value)) if len(token) > 2}


def match_application(*, subject: str | None, sender: str | None, candidates: list[ApplicationCandidate]) -> ApplicationMatch:
    haystack = f"{normalize(subject)} {normalize(sender)}"
    scored: list[tuple[float, ApplicationCandidate, tuple[str, ...]]] = []
    for candidate in candidates:
        company_tokens = _tokens(candidate.company_name) - GENERIC_COMPANY_WORDS
        title_tokens = _tokens(candidate.job_title)
        company_hits = company_tokens & _tokens(haystack)
        title_hits = title_tokens & _tokens(haystack)
        if not company_hits:
            continue
        score = 0.55 + min(0.25, 0.12 * len(company_hits)) + min(0.2, 0.08 * len(title_hits))
        reasons = (f"Employer evidence: {', '.join(sorted(company_hits))}",)
        if title_hits:
            reasons += (f"Role evidence: {', '.join(sorted(title_hits))}",)
        scored.append((score, candidate, reasons))
    if not scored:
        return ApplicationMatch(None, 0.0, ("No distinctive owned application evidence found",))
    scored.sort(key=lambda item: item[0], reverse=True)
    best = scored[0]
    if len(scored) > 1 and scored[1][0] >= best[0] - 0.05:
        return ApplicationMatch(None, best[0], ("Multiple owned applications are similarly plausible",), True)
    return ApplicationMatch(best[1].id, min(best[0], 0.99), best[2])
