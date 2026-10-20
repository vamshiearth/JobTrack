from datetime import date
import pytest
from pydantic import ValidationError

from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
    ApplicationStage,
    NextActionOwner,
)


def test_valid_application_create():
    data = ApplicationCreate(
        company_name="Example Technologies",
        job_title="Software Engineer",
        applied_at="2026-10-20",
    )

    assert data.company_name == "Example Technologies"
    assert data.job_title == "Software Engineer"
    assert data.applied_at == date(2026, 10, 20)


@pytest.mark.parametrize("company_name", ["", "   "])
def test_blank_company_rejected(company_name):
    with pytest.raises(ValidationError):
        ApplicationCreate(company_name=company_name, job_title="Developer")


def test_blank_job_title_rejected():
    with pytest.raises(ValidationError):
        ApplicationCreate(company_name="Example", job_title=" ")


def test_invalid_job_url_rejected():
    with pytest.raises(ValidationError):
        ApplicationCreate(
            company_name="Example",
            job_title="Developer",
            job_url="not-a-url",
        )


def test_update_allows_optional_field_clearing():
    update = ApplicationUpdate(location=None, notes=None)

    assert update.model_dump(exclude_unset=True) == {"location": None, "notes": None}


def test_update_rejects_status_and_ownership_fields():
    with pytest.raises(ValidationError):
        ApplicationUpdate(current_stage="REJECTED")


def test_application_response_uses_database_enum_values():
    assert ApplicationStage("APPLIED") is ApplicationStage.APPLIED
    assert NextActionOwner("EMPLOYER") is NextActionOwner.EMPLOYER


def test_application_response_requires_identity_and_timestamps():
    with pytest.raises(ValidationError):
        ApplicationResponse(company_name="Example", job_title="Developer")


def test_application_create_does_not_accept_client_ownership_or_progress():
    with pytest.raises(ValidationError):
        ApplicationCreate(
            company_name="Example",
            job_title="Developer",
            user_id="not-authorized",
            current_stage="REJECTED",
        )