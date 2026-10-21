import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_id
from app.models import ApplicationPreparation
from app.schemas.application_preparation import ApplicationPreparationResponse, PreparationUpdate
from app.schemas.application_handoff import HandoffResponse, SubmissionConfirmationRequest, SubmissionConfirmationResponse
from app.services.application_preparation import create_preparation, get_preparation, update_preparation
from app.services.application_handoff import HandoffConflict, confirm_submission, create_handoff

router = APIRouter(prefix="/preparations", tags=["Application Preparation"])


@router.get("", response_model=list[ApplicationPreparationResponse])
def list_preparations(user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return list(db.scalars(
        select(ApplicationPreparation)
        .where(ApplicationPreparation.user_id == user_id)
        .order_by(ApplicationPreparation.updated_at.desc())
    ).all())


@router.post("/opportunities/{opportunity_id}", response_model=ApplicationPreparationResponse, status_code=201)
def prepare_opportunity(opportunity_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    preparation = create_preparation(db, user_id=user_id, opportunity_id=opportunity_id)
    if preparation is None:
        raise HTTPException(status_code=404, detail="Opportunity or candidate profile not found")
    db.commit()
    return preparation


@router.get("/{preparation_id}", response_model=ApplicationPreparationResponse)
def read_preparation(preparation_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    preparation = get_preparation(db, user_id=user_id, preparation_id=preparation_id)
    if preparation is None:
        raise HTTPException(status_code=404, detail="Preparation not found")
    db.commit()
    return preparation


@router.patch("/{preparation_id}", response_model=ApplicationPreparationResponse)
def patch_preparation(preparation_id: uuid.UUID, payload: PreparationUpdate, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    preparation = update_preparation(db, user_id=user_id, preparation_id=preparation_id, data=payload)
    if preparation is None:
        raise HTTPException(status_code=404, detail="Preparation not found or is stale")
    db.commit()
    return preparation


@router.post("/{preparation_id}/handoff", response_model=HandoffResponse, status_code=201)
def handoff_preparation(preparation_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        handoff = create_handoff(db, user_id=user_id, preparation_id=preparation_id)
    except HandoffConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if handoff is None:
        raise HTTPException(status_code=404, detail="Preparation not found")
    db.commit()
    return handoff


@router.post("/{preparation_id}/confirm-submission", response_model=SubmissionConfirmationResponse, status_code=201)
def confirm_preparation_submission(preparation_id: uuid.UUID, payload: SubmissionConfirmationRequest, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        confirmation = confirm_submission(db, user_id=user_id, preparation_id=preparation_id, data=payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HandoffConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return confirmation


@router.get("/{preparation_id}/submission", response_model=SubmissionConfirmationResponse)
def read_submission_confirmation(preparation_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    from sqlalchemy import select
    from app.models import ApplicationSubmissionConfirmation

    confirmation = db.scalar(select(ApplicationSubmissionConfirmation).where(ApplicationSubmissionConfirmation.preparation_id == preparation_id, ApplicationSubmissionConfirmation.user_id == user_id))
    if confirmation is None:
        raise HTTPException(status_code=404, detail="Submission confirmation not found")
    return confirmation
