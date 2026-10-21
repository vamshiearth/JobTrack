from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.db.session import SessionLocal
from app.dependencies.auth import get_current_user_id
from app.main import app
from app.models import (
    ApplicationEvent,
    ApplicationPreparation,
    ApplicationSubmissionConfirmation,
    JobApplication,
    User,
)
from app.schemas.application_handoff import SubmissionConfirmationRequest
from app.services.application_handoff import HandoffConflict, confirm_submission, create_handoff


def _create_approved_preparation():
    user_id = uuid4()
    with SessionLocal() as db:
        user = User(id=user_id, email=f"concurrency-{user_id}@example.com")
        db.add(user)
        db.commit()

    app.dependency_overrides[get_current_user_id] = lambda: user_id
    try:
        with TestClient(app) as client:
            assert client.put(
                "/api/v1/candidate-profile",
                json={"skills": ["Python"], "target_roles": ["Engineer"], "resume_version": "r1"},
            ).status_code == 200
            opportunity = client.post(
                "/api/v1/opportunities",
                json={"company_name": "Example", "job_title": "Engineer", "source_url": "https://jobs.example.com/engineer"},
            ).json()
            preparation = client.post(f"/api/v1/preparations/opportunities/{opportunity['id']}").json()
            response = client.patch(
                f"/api/v1/preparations/{preparation['id']}",
                json={
                    "application_answers": [
                        {"question_key": "work_authorization", "answer": "Yes", "status": "RESOLVED"},
                        {"question_key": "sponsorship", "answer": "No", "status": "RESOLVED"},
                    ],
                    "status": "APPROVED",
                },
            )
            assert response.status_code == 200
            preparation = response.json()
            handoff = client.post(f"/api/v1/preparations/{preparation['id']}/handoff")
            assert handoff.status_code == 201
            return user_id, preparation, handoff.json()
    finally:
        app.dependency_overrides.clear()


def _run_competing_confirmations(user_id, preparation, handoff, keys):
    barrier = Barrier(2)

    def worker(key):
        with SessionLocal() as db:
            backend_pid = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            barrier.wait(timeout=10)
            try:
                result = confirm_submission(
                    db,
                    user_id=user_id,
                    preparation_id=preparation["id"],
                    data=SubmissionConfirmationRequest(
                        expected_revision=preparation["draft_revision"],
                        idempotency_key=key,
                        user_confirmed_submission=True,
                        handoff_id=handoff["id"],
                    ),
                )
                db.commit()
                return "success", result.job_application_id, backend_pid
            except HandoffConflict:
                db.rollback()
                return "conflict", None, backend_pid

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(worker, keys))
    assert results[0][2] != results[1][2]
    return results


@pytest.mark.parametrize("keys", [("same-key", "same-key"), ("key-a", "key-b")])
def test_simultaneous_confirmations_are_serialized(keys):
    user_id, preparation, handoff = _create_approved_preparation()
    suffix = str(uuid4())
    keys = tuple(f"{key}-{suffix}" for key in keys)
    try:
        _run_competing_confirmations(user_id, preparation, handoff, keys)

        with SessionLocal() as db:
            confirmations = db.scalars(
                select(ApplicationPreparation).where(ApplicationPreparation.id == preparation["id"])
            ).all()
            application_count = db.scalar(select(func.count(JobApplication.id)).where(JobApplication.user_id == user_id))
            event_count = db.scalar(
                select(func.count(ApplicationEvent.id)).where(
                    ApplicationEvent.event_kind == "APPLICATION_SUBMITTED",
                    ApplicationEvent.job_application_id == JobApplication.id,
                    JobApplication.user_id == user_id,
                )
            )
            confirmation_count = db.scalar(
                select(func.count(ApplicationSubmissionConfirmation.id)).where(
                    ApplicationSubmissionConfirmation.preparation_id == preparation["id"]
                )
            )

        assert len(confirmations) == 1
        assert confirmation_count == 1
        assert application_count == 1
        assert event_count == 1
    finally:
        with SessionLocal() as db:
            for table in (
                "application_submission_confirmations",
                "application_handoffs",
                "job_applications",
                "application_preparations",
                "job_opportunities",
                "candidate_profiles",
                "review_items",
                "gmail_connections",
            ):
                db.execute(text(f"DELETE FROM {table} WHERE user_id = :user_id"), {"user_id": user_id})
            db.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
            db.commit()
