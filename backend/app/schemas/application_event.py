from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventKind(str, Enum):
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    RECRUITER_CONTACTED = "RECRUITER_CONTACTED"
    ASSESSMENT_INVITED = "ASSESSMENT_INVITED"
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED"
    OFFER_RECEIVED = "OFFER_RECEIVED"
    REJECTION_RECEIVED = "REJECTION_RECEIVED"
    APPLICATION_WITHDRAWN = "APPLICATION_WITHDRAWN"


class ApplicationEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_kind: EventKind
    occurred_at: datetime
    client_request_id: UUID
    interview_round: int | None = Field(default=None, ge=1)
    details: dict[str, Any] | None = None

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include timezone information")
        return value

    @model_validator(mode="after")
    def validate_interview_round(self):
        interview_event = self.event_kind in {
            EventKind.INTERVIEW_SCHEDULED,
            EventKind.INTERVIEW_COMPLETED,
        }
        if interview_event and self.interview_round is None:
            raise ValueError("interview events require interview_round")
        if not interview_event and self.interview_round is not None:
            raise ValueError("interview_round is only valid for interview events")
        return self


class ApplicationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_application_id: UUID
    event_kind: EventKind
    interview_round: int | None
    origin: str
    verified_by_user: bool
    details: dict[str, Any] | None
    occurred_at: datetime
    recorded_at: datetime


class ApplicationEventListResponse(BaseModel):
    items: list[ApplicationEventResponse]