import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_id
from app.models import ApplicationEvent
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdate,
)
from app.services.application_service import (
    create_application,
    delete_application,
    get_application,
    list_applications,
    update_application,
)


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
    db.commit()
    return application


@router.get("", response_model=ApplicationListResponse)
def get_job_applications(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    applications = list_applications(db, user_id=user_id)
    return ApplicationListResponse(items=applications, total=len(applications))


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_job_application_detail(
    application_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    application = get_application(db, user_id=user_id, application_id=application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.patch("/{application_id}", response_model=ApplicationResponse)
def patch_job_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    application = update_application(
        db, user_id=user_id, application_id=application_id, data=payload
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    db.commit()
    return application


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_application(
    application_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not delete_application(db, user_id=user_id, application_id=application_id):
        raise HTTPException(status_code=404, detail="Application not found")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)