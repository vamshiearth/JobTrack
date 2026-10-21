from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PreparationStatus(str, Enum):
    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"


class PreparationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_suggestions: list[dict[str, Any]] | None = None
    application_answers: list[dict[str, Any]] | None = None
    review_notes: str | None = Field(default=None, max_length=5000)
    status: PreparationStatus | None = None


class ApplicationPreparationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    opportunity_id: UUID
    candidate_profile_id: UUID
    match_assessment_id: UUID | None
    source_fingerprint: str
    draft_revision: int
    status: PreparationStatus
    resume_suggestions: list[dict[str, Any]]
    application_answers: list[dict[str, Any]]
    review_notes: str | None
    approved_at: datetime | None
    approved_revision: int | None
    created_at: datetime
    updated_at: datetime
