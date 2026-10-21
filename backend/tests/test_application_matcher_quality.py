import uuid

from app.services.application_matcher import (
    ApplicationCandidate,
    match_application,
    sender_domain,
)


def app(company: str, role: str) -> ApplicationCandidate:
    return ApplicationCandidate(uuid.uuid4(), company, role)


def test_distinct_company_subject_match():
    target = app("Acme Robotics", "Backend Engineer")
    other = app("Northstar Analytics", "Data Analyst")
    result = match_application(subject="Acme Robotics interview invitation", sender="notifications@greenhouse.io", applications=[target, other])
    assert result.application_id == target.id
    assert not result.ambiguous


def test_compact_employer_domain_match():
    target = app("Acme Robotics", "Backend Engineer")
    result = match_application(subject="Interview invitation", sender="recruiting@acmerobotics.com", applications=[target])
    assert result.application_id == target.id


def test_shared_platform_domain_is_not_employer_proof():
    target = app("Acme Robotics", "Backend Engineer")
    result = match_application(subject="Interview invitation", sender="notifications@greenhouse.io", applications=[target])
    assert result.application_id is None


def test_distinctive_role_breaks_same_employer_tie():
    backend = app("Acme Robotics", "Backend Engineer")
    frontend = app("Acme Robotics", "Frontend Developer")
    result = match_application(subject="Acme Robotics Backend interview", sender="recruiting@acme.com", applications=[backend, frontend])
    assert result.application_id == backend.id


def test_generic_role_keeps_same_employer_ambiguous():
    first = app("Acme Robotics", "Backend Engineer")
    second = app("Acme Robotics", "Software Engineer")
    result = match_application(subject="Acme Robotics interview", sender="recruiting@acme.com", applications=[first, second])
    assert result.application_id is None
    assert result.ambiguous


def test_same_employer_same_role_is_ambiguous():
    first = app("Acme Robotics", "Backend Engineer")
    second = app("Acme Robotics", "Backend Engineer")
    result = match_application(subject="Acme Robotics Backend Engineer interview", sender="recruiting@acme.com", applications=[first, second])
    assert result.application_id is None
    assert result.ambiguous


def test_generic_interview_has_no_match():
    target = app("Acme Robotics", "Backend Engineer")
    result = match_application(subject="Interview invitation", sender="recruiting@acme.com", applications=[target])
    assert result.application_id is None


def test_generic_platform_sender_display_name_is_not_proof():
    target = app("Acme Robotics", "Backend Engineer")
    result = match_application(subject="Interview invitation", sender='"Acme Robotics" <notifications@greenhouse.io>', applications=[target])
    assert result.application_id is None


def test_unknown_sender_and_employer_is_unmatched():
    target = app("Acme Robotics", "Backend Engineer")
    result = match_application(subject="A message about an opportunity", sender="unknown@provider.test", applications=[target])
    assert result.application_id is None


def test_different_employer_is_not_selected():
    target = app("Acme Robotics", "Backend Engineer")
    result = match_application(subject="Northstar Analytics interview", sender="recruiting@northstaranalytics.com", applications=[target])
    assert result.application_id is None


def test_sender_domain_parses_display_names():
    assert sender_domain('Recruiting Team <recruiting@acmerobotics.com>') == "acmerobotics.com"


def test_candidate_keyword_remains_compatible():
    target = app("Acme Robotics", "Backend Engineer")
    result = match_application(subject="Acme Robotics interview", sender="recruiting@acme.com", candidates=[target])
    assert result.application_id == target.id
