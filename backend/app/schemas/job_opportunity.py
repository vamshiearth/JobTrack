from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class OpportunityStatus(str, Enum):
    SAVED = "SAVED"
    ARCHIVED = "ARCHIVED"


class OpportunitySourceType(str, Enum):
    MANUAL = "MANUAL"


class WorkArrangement(str, Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    UNKNOWN = "UNKNOWN"


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    UNKNOWN = "UNKNOWN"


class JobOpportunityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1, max_length=255)
    job_title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    work_arrangement: WorkArrangement | None = None
    employment_type: EmploymentType | None = None
    description: str | None = None
    source_type: OpportunitySourceType = OpportunitySourceType.MANUAL
    source_job_id: str | None = Field(default=None, max_length=255)
    source_url: HttpUrl

    @field_validator("company_name", "job_title")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class JobOpportunityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    job_title: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    work_arrangement: WorkArrangement | None = None
    employment_type: EmploymentType | None = None
    description: str | None = None
    status: OpportunityStatus | None = None

    @field_validator("company_name", "job_title")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("must not be null")
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class JobOpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    source_type: OpportunitySourceType
    source_job_id: str | None
    company_name: str
    job_title: str
    location: str | None
    work_arrangement: WorkArrangement | None
    employment_type: EmploymentType | None
    description: str | None
    source_url: HttpUrl
    normalized_url: HttpUrl
    status: OpportunityStatus
    created_at: datetime
    updated_at: datetime


class JobOpportunityListResponse(BaseModel):
    items: list[JobOpportunityResponse]
    total: int
    page: int
    page_size: int
