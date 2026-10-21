import re
from dataclasses import dataclass
from email.utils import parseaddr
from uuid import UUID

from app.services.recruitment_classifier import normalize

GENERIC_COMPANY_WORDS = frozenset({"company", "technologies", "technology", "solutions", "systems", "software", "services", "inc", "llc", "corp", "corporation", "group", "the", "limited", "ltd", "careers", "jobs"})
GENERIC_ROLE_WORDS = frozenset({"engineer", "engineering", "developer", "development", "software", "position", "role", "job", "opening", "opportunity", "associate", "junior", "senior"})
SHARED_MAIL_DOMAINS = frozenset({"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "greenhouse.io", "lever.co", "myworkday.com", "workday.com", "workdayjobs.com"})
GENERIC_SENDER_DOMAINS = frozenset({"example.com", "example.org", "example.net"})


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


def sender_domain(sender: str | None) -> str | None:
    address = parseaddr(sender or "")[1].casefold()
    domain = address.rsplit("@", 1)[-1].strip()
    return domain or None


def _compact(value: str) -> str:
    return "".join(sorted(_tokens(value) - GENERIC_COMPANY_WORDS))


def match_application(*, subject: str | None, sender: str | None, candidates: list[ApplicationCandidate] | None = None, applications: list[ApplicationCandidate] | None = None) -> ApplicationMatch:
    candidate_list = candidates if candidates is not None else applications or []
    subject_tokens = _tokens(subject or "")
    domain = sender_domain(sender)
    haystack = normalize(subject)
    haystack_tokens = _tokens(haystack)
    scored: list[tuple[float, ApplicationCandidate, tuple[str, ...]]] = []
    for candidate in candidate_list:
        company_tokens = _tokens(candidate.company_name) - GENERIC_COMPANY_WORDS
        role_tokens = _tokens(candidate.job_title) - GENERIC_ROLE_WORDS
        company_hits = company_tokens & haystack_tokens
        domain_match = bool(domain and not any(domain == generic or domain.endswith(f".{generic}") for generic in GENERIC_SENDER_DOMAINS) and domain not in SHARED_MAIL_DOMAINS and _compact(candidate.company_name) and _compact(candidate.company_name) in domain.replace(".", ""))
        title_hits = role_tokens & subject_tokens
        if not company_hits and not domain_match:
            continue
        score = 0.62 if domain_match else 0.55 + min(0.25, 0.12 * len(company_hits))
        score += min(0.25, 0.12 * len(title_hits))
        reasons = ((f"Employer domain evidence: {domain}",) if domain_match else (f"Employer evidence: {', '.join(sorted(company_hits))}",))
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
