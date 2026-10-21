import pytest

from app.services.recruitment_classifier import (
    RecruitmentCategory,
    classify_recruitment_email,
)


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("We received your application", RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT),
        ("Thank you for applying", RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT),
        ("Application confirmation", RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT),
        ("Your application has been received", RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT),
        ("Thanks for applying to Example Corp", RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT),
        ("Recruiter reaching out about a position", RecruitmentCategory.RECRUITER_CONTACT),
        ("Let's discuss your application", RecruitmentCategory.RECRUITER_CONTACT),
        ("Are you still interested in these jobs?", RecruitmentCategory.RECRUITER_CONTACT),
        ("Complete your coding assessment", RecruitmentCategory.ASSESSMENT_INVITATION),
        ("Schedule your interview", RecruitmentCategory.INTERVIEW_INVITATION),
        ("Your one-time passcode", RecruitmentCategory.UNKNOWN),
        ("Your verification code", RecruitmentCategory.UNKNOWN),
        ("New job alerts for you", RecruitmentCategory.UNKNOWN),
        ("Jobs you might like", RecruitmentCategory.UNKNOWN),
        ("Weekly career digest", RecruitmentCategory.UNKNOWN),
    ],
)
def test_audit_subjects_use_conservative_categories(subject, expected):
    result = classify_recruitment_email(subject=subject, sender="recruiter@example.com")

    assert result.category == expected
    assert result.requires_review


def test_sender_name_does_not_establish_recruiter_contact():
    result = classify_recruitment_email(
        subject="A message about an opportunity",
        sender="Recruiter Team <recruiter@example.com>",
    )

    assert result.category == RecruitmentCategory.UNKNOWN


def test_application_acknowledgment_has_no_recruiter_event():
    result = classify_recruitment_email(
        subject="Thank you for applying",
        sender="Recruiting Platform <notifications@example.com>",
    )

    assert result.category == RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT
