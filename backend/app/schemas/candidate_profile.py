from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CandidateProfileUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[str] = Field(default_factory=list, max_length=100)
    experience_summary: str | None = None
    target_roles: list[str] = Field(default_factory=list, max_length=30)
    preferred_locations: list[str] = Field(default_factory=list, max_length=30)
    remote_preference: str | None = Field(default=None, max_length=20)
    resume_version: str = Field(min_length=1, max_length=255)

    @field_validator("skills", "target_roles", "preferred_locations")
    @classmethod
    def clean_values(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if len(cleaned) != len(set(value.casefold() for value in cleaned)):
            raise ValueError("values must be unique")
        return cleaned


class CandidateProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    skills: list[str]
    experience_summary: str | None
    target_roles: list[str]
    preferred_locations: list[str]
    remote_preference: str | None
    resume_version: str
    revision: int
    created_at: datetime
    updated_at: datetime