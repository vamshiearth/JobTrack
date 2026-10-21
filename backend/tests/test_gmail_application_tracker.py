from app.services.gmail_application_tracker import extract_application_evidence
from app.services.recruitment_classifier import RecruitmentCategory, classify_recruitment_email


def test_extracts_role_and_company_from_acknowledgment_subject():
    evidence = extract_application_evidence(
        subject="Application received: Backend Engineer at Acme Corp",
        sender="careers@acme.com",
    )

    assert evidence.company_name == "Acme Corp"
    assert evidence.job_title == "Backend Engineer"


def test_requires_role_when_sender_only_identifies_company():
    evidence = extract_application_evidence(
        subject="Thank you for applying to Acme Corp",
        sender="careers@acme.com",
    )

    assert evidence.company_name == "Acme"
    assert evidence.job_title is None


def test_does_not_turn_marketing_apply_subject_into_evidence():
    evidence = extract_application_evidence(
        subject="Apply now for our latest openings",
        sender="jobs@acme.com",
    )

    assert evidence.company_name == "Acme"
    assert evidence.job_title is None


def test_classifies_status_subjects_without_using_email_bodies():
    assert classify_recruitment_email(
        subject="Coding assessment for SDE I", sender="jobs@amazon.com"
    ).category == RecruitmentCategory.ASSESSMENT_INVITATION
    assert classify_recruitment_email(
        subject="Interview invitation: CPQ Developer", sender="careers@oracle.com"
    ).category == RecruitmentCategory.INTERVIEW_INVITATION
    assert classify_recruitment_email(
        subject="We are pleased to offer you a role", sender="careers@oracle.com"
    ).category == RecruitmentCategory.OFFER_POSSIBLE
    assert classify_recruitment_email(
        subject="Your application was not selected", sender="careers@oracle.com"
    ).category == RecruitmentCategory.REJECTION_POSSIBLE