import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_id
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStage,
    ApplicationUpdate,
    NextActionOwner,
)
from app.services.application_service import (
    create_application_with_submission_event,
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
    application = create_application_with_submission_event(db, user_id=user_id, data=payload)
    db.commit()
    db.refresh(application)
    return application
@router.get("", response_model=ApplicationListResponse)
def get_job_applications(
    q: str | None = Query(default=None, max_length=200),
    stage: ApplicationStage | None = None,
    next_action_owner: NextActionOwner | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: Literal["last_activity_at", "applied_at", "company_name"] = "last_activity_at",
    sort_order: Literal["asc", "desc"] = "desc",
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    applications, total = list_applications(
        db,
        user_id=user_id,
        q=q,
        stage=stage,
        next_action_owner=next_action_owner,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ApplicationListResponse(
        items=applications,
        total=total,
        page=page,
        page_size=page_size,
    )


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