from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SubmissionConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=255)
    user_confirmed_submission: bool
    handoff_id: UUID | None = None
    employer_confirmation_reference: str | None = Field(default=None, max_length=255)


class HandoffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    preparation_id: UUID
    approved_revision: int
    source_url_snapshot: str
    opened_at: datetime
    created_at: datetime


class SubmissionConfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    preparation_id: UUID
    handoff_id: UUID | None
    job_application_id: UUID
    confirmation_method: str
    employer_confirmation_reference: str | None
    confirmed_at: datetime
    idempotency_key: str