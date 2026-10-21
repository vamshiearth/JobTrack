import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_id
from app.schemas.application_preparation import ApplicationPreparationResponse, PreparationUpdate
from app.services.application_preparation import create_preparation, get_preparation, update_preparation

router = APIRouter(prefix="/preparations", tags=["Application Preparation"])


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
