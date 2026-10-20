from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReviewEvidenceResponse(BaseModel):
    sender: str | None
    subject: str | None
    received_at: datetime


class ReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    category: str
    candidate_application_id: UUID | None
    proposed_event_type: str | None
    reasons: list[str]
    evidence: ReviewEvidenceResponse
    created_at: datetime
    decided_at: datetime | None


class ReviewItemListResponse(BaseModel):
    items: list[ReviewItemResponse]
    total: int
    page: int
    page_size: int


class ApproveReviewRequest(BaseModel):
    application_id: UUID
    interview_round: int | None = Field(default=None, ge=1)


class ReviewDecisionResponse(BaseModel):
    review_id: UUID
    status: str
    application_id: UUID | None
    created_event_id: UUID | None