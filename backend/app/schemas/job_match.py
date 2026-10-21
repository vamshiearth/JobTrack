from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    candidate_profile_id: UUID
    profile_revision: int
    opportunity_updated_at: datetime
    scoring_model_version: str
    score: int | None
    evidence_coverage: float
    matched_skills: list[str]
    unverified_requirements: list[str]
    explanations: list[str]
    eligibility_status: str
    ranking_status: str
    created_at: datetime