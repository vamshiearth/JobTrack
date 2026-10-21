from uuid import UUID

from pydantic import BaseModel


class DiscoveryMatchSummary(BaseModel):
    score: int | None
    ranking_status: str
    eligibility_status: str
    matched_skills: list[str]
    unverified_requirements: list[str]
    explanations: list[str]


class DiscoveryJobResult(BaseModel):
    id: UUID
    company_name: str
    job_title: str
    location: str | None
    source_url: str
    availability_status: str
    work_arrangement: str | None
    location_restrictions: str | None
    already_saved: bool
    match: DiscoveryMatchSummary | None


class DiscoverySearchResponse(BaseModel):
    items: list[DiscoveryJobResult]
    total: int
    limit: int
    offset: int
