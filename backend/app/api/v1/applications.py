import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_id
from app.models import ApplicationEvent
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
)
from app.services.application_service import create_application, list_applications


router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_job_application(
    payload: ApplicationCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    application = create_application(db, user_id=user_id, data=payload)
    db.add(
        ApplicationEvent(
            job_application_id=application.id,
            event_kind="APPLICATION_SUBMITTED",
            origin="MANUAL",
            verified_by_user=True,
            idempotency_key=f"application-created-{application.id}",
            occurred_at=datetime.now(timezone.utc),
        )
    )
    db.flush()
    return application


@router.get("", response_model=ApplicationListResponse)
def get_job_applications(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    applications = list_applications(db, user_id=user_id)
    return ApplicationListResponse(items=applications, total=len(applications))