from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_id
from app.schemas.application_event import (
    ApplicationEventCreate,
    ApplicationEventListResponse,
    ApplicationEventResponse,
)
from app.services.application_event_service import (
    ApplicationNotFound,
    EventConflict,
    list_application_events,
    record_application_event,
)


router = APIRouter(
    prefix="/applications/{application_id}/events",
    tags=["Application Events"],
)


@router.get("", response_model=ApplicationEventListResponse)
def get_application_events(
    application_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        items, total = list_application_events(
            db, user_id=user_id, application_id=application_id
        )
        return ApplicationEventListResponse(items=items, total=total)
    except ApplicationNotFound:
        raise HTTPException(status_code=404, detail="Application not found")


@router.post("", response_model=ApplicationEventResponse, status_code=status.HTTP_201_CREATED)
def create_application_event(
    application_id: UUID,
    payload: ApplicationEventCreate,
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        event, created = record_application_event(
            db, user_id=user_id, application_id=application_id, data=payload
        )
    except ApplicationNotFound:
        raise HTTPException(status_code=404, detail="Application not found")
    except EventConflict as error:
        raise HTTPException(status_code=409, detail=str(error))
    db.commit()
    if not created:
        response.status_code = status.HTTP_200_OK
    return event