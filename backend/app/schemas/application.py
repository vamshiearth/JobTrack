from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ApplicationStage(str, Enum):
    APPLIED = "APPLIED"
    SCREENING = "SCREENING"
    ASSESSMENT = "ASSESSMENT"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class NextActionOwner(str, Enum):
    USER = "USER"
    EMPLOYER = "EMPLOYER"
    NONE = "NONE"


class ApplicationSource(str, Enum):
    MANUAL = "MANUAL"
    EMAIL = "EMAIL"


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1, max_length=255)
    job_title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    job_url: HttpUrl | None = None
    applied_at: date | None = None
    notes: str | None = None

    @field_validator("company_name", "job_title")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    job_title: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    job_url: HttpUrl | None = None
    applied_at: date | None = None
    notes: str | None = None

    @field_validator("company_name", "job_title")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("must not be null")
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    company_name: str
    job_title: str
    job_url: HttpUrl | None
    location: str | None
    applied_at: date | None
    application_source: ApplicationSource
    current_stage: ApplicationStage
    next_action_owner: NextActionOwner
    notes: str | None
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class ApplicationListResponse(BaseModel):
    items: list[ApplicationResponse]
    total: int