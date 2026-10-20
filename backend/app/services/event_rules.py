from app.schemas.application_event import EventKind


EVENT_STATUS = {
    EventKind.APPLICATION_SUBMITTED: ("APPLIED", "EMPLOYER"),
    EventKind.RECRUITER_CONTACTED: ("SCREENING", "USER"),
    EventKind.ASSESSMENT_INVITED: ("ASSESSMENT", "USER"),
    EventKind.ASSESSMENT_COMPLETED: ("ASSESSMENT", "EMPLOYER"),
    EventKind.INTERVIEW_SCHEDULED: ("INTERVIEW", "USER"),
    EventKind.INTERVIEW_COMPLETED: ("INTERVIEW", "EMPLOYER"),
    EventKind.OFFER_RECEIVED: ("OFFER", "USER"),
    EventKind.REJECTION_RECEIVED: ("REJECTED", "NONE"),
    EventKind.APPLICATION_WITHDRAWN: ("WITHDRAWN", "NONE"),
}

CLOSED_STAGES = {"REJECTED", "WITHDRAWN"}


def get_status_for_event(event_kind: EventKind) -> tuple[str, str]:
    return EVENT_STATUS[event_kind]