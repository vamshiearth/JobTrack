import uuid

from app.services.application_matcher import ApplicationCandidate, match_application
from app.services.recruitment_classifier import RecruitmentCategory, classify_recruitment_email
from app.services.recruitment_proposals import build_recruitment_proposal


def candidate(company: str, role: str) -> ApplicationCandidate:
    return ApplicationCandidate(uuid.uuid4(), company, role)


def test_assessment_invitation_classified():
    result = classify_recruitment_email(subject="Complete your assessment", sender="recruiter@example.com")
    assert result.category == RecruitmentCategory.ASSESSMENT_INVITATION
    assert result.requires_review


def test_interview_invitation_classified():
    assert classify_recruitment_email(subject="Interview invitation", sender=None).category == RecruitmentCategory.INTERVIEW_INVITATION


def test_application_acknowledgment_classified():
    assert classify_recruitment_email(subject="Application received", sender=None).category == RecruitmentCategory.APPLICATION_ACKNOWLEDGMENT


def test_unknown_is_not_proposed():
    result = classify_recruitment_email(subject="Weekly newsletter", sender="news@example.com")
    assert result.category == RecruitmentCategory.UNKNOWN


def test_distinctive_company_matches():
    application = candidate("Acme Robotics", "Backend Engineer")
    match = match_application(subject="Acme Robotics interview", sender="talent@acme.com", candidates=[application])
    assert match.application_id == application.id


def test_generic_sender_does_not_match():
    application = candidate("Example Software", "Software Engineer")
    match = match_application(subject="Your interview", sender="no-reply@jobs.example.com", candidates=[application])
    assert match.application_id is None


def test_similar_applications_are_ambiguous():
    first = candidate("Acme", "Backend Engineer")
    second = candidate("Acme", "Frontend Engineer")
    match = match_application(subject="Acme interview", sender="recruiting@acme.com", candidates=[first, second])
    assert match.application_id is None
    assert match.ambiguous


def test_proposal_maps_event_without_applying_it():
    classification = classify_recruitment_email(subject="Interview invitation", sender="recruiting@acme.com")
    application = candidate("Acme", "Engineer")
    match = match_application(subject="Acme interview", sender="recruiting@acme.com", candidates=[application])
    proposal = build_recruitment_proposal(classification, match)
    assert proposal is not None
    assert proposal.proposed_event_type == "INTERVIEW_SCHEDULED"
    assert proposal.requires_review


def test_unmatched_recruitment_message_remains_reviewable():
    classification = classify_recruitment_email(subject="Complete your assessment", sender="recruiter@example.com")
    match = match_application(subject="Complete your assessment", sender="recruiter@example.com", candidates=[])
    proposal = build_recruitment_proposal(classification, match)
    assert proposal is not None
    assert proposal.application_id is None
    assert proposal.requires_review
