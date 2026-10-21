import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

from sqlalchemy import delete, select

from app.db.session import SessionLocal, engine
from app.models import ApplicationEvent, EmailMessage, GmailConnection, JobApplication, ReviewItem, User
from app.services.review_decisions import approve_review


def test_competing_approvals_create_one_event():
    setup = SessionLocal()
    owner = User(email=f"concurrency-{uuid.uuid4()}@example.com")
    connection = GmailConnection(
        user=owner,
        google_subject=f"google-{uuid.uuid4()}",
        email_address=owner.email,
        granted_scopes=["https://www.googleapis.com/auth/gmail.metadata"],
        connection_status="CONNECTED",
    )
    application = JobApplication(
        user=owner,
        company_name="Concurrency Co",
        job_title="Developer",
        application_source="MANUAL",
        current_stage="APPLIED",
        next_action_owner="USER",
        last_activity_at=datetime.now(timezone.utc),
    )
    message = EmailMessage(
        gmail_connection=connection,
        gmail_message_id=str(uuid.uuid4()),
        gmail_thread_id=str(uuid.uuid4()),
        sender_address="careers@example.com",
        subject="Recruitment update",
        received_at=datetime.now(timezone.utc),
        classification_kind="RECRUITMENT_SIGNAL",
        processing_status="CLASSIFIED",
    )
    review = ReviewItem(
        user=owner,
        email_message=message,
        suggested_application=application,
        suggested_event_kind="RECRUITER_CONTACTED",
        confidence="0.900",
        reason="concurrency regression",
        review_status="PENDING",
    )
    setup.add(review)
    setup.commit()
    review_id = review.id
    owner_id = owner.id
    application_id = application.id
    setup.close()

    barrier = Barrier(2)

    def attempt_approval():
        db = SessionLocal()
        try:
            barrier.wait(timeout=10)
            result = approve_review(
                db,
                review_id=review_id,
                user_id=owner_id,
                application_id=application_id,
                interview_round=None,
            )
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt_approval(), range(2)))

        verify = SessionLocal()
        try:
            events = verify.scalars(
                select(ApplicationEvent).where(
                    ApplicationEvent.job_application_id == application_id
                )
            ).all()
            saved_review = verify.get(ReviewItem, review_id)
            assert len(events) == 1
            assert saved_review is not None
            assert saved_review.review_status == "APPROVED"
            assert {result.created_event_id for result in results} == {events[0].id}
        finally:
            verify.close()
    finally:
        cleanup = SessionLocal()
        try:
            cleanup.execute(delete(ApplicationEvent).where(ApplicationEvent.job_application_id == application_id))
            cleanup.execute(delete(ReviewItem).where(ReviewItem.id == review_id))
            cleanup.execute(delete(EmailMessage).where(EmailMessage.gmail_connection_id == connection.id))
            cleanup.execute(delete(GmailConnection).where(GmailConnection.id == connection.id))
            cleanup.execute(delete(JobApplication).where(JobApplication.id == application_id))
            cleanup.execute(delete(User).where(User.id == owner_id))
            cleanup.commit()
        finally:
            cleanup.close()
