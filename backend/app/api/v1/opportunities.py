import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_id
from app.schemas.job_opportunity import (
    JobOpportunityCreate,
    JobOpportunityListResponse,
    JobOpportunityResponse,
    JobOpportunityUpdate,
    OpportunityStatus,
)
from app.services.job_opportunities import (
    create_opportunity,
    get_opportunity,
    list_opportunities,
    update_opportunity,
)


router = APIRouter(prefix="/opportunities", tags=["Opportunities"])


@router.post("", response_model=JobOpportunityResponse, status_code=status.HTTP_201_CREATED)
def import_opportunity(payload: JobOpportunityCreate, response: Response, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    opportunity, created = create_opportunity(db, user_id=user_id, data=payload)
    db.commit()
    if not created:
        response.status_code = status.HTTP_200_OK
    return opportunity


@router.get("", response_model=JobOpportunityListResponse)
def get_opportunities(status_filter: OpportunityStatus | None = Query(default=None, alias="status"), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    items, total = list_opportunities(db, user_id=user_id, status=status_filter, page=page, page_size=page_size)
    return JobOpportunityListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{opportunity_id}", response_model=JobOpportunityResponse)
def get_opportunity_detail(opportunity_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    opportunity = get_opportunity(db, user_id=user_id, opportunity_id=opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity


@router.patch("/{opportunity_id}", response_model=JobOpportunityResponse)
def patch_opportunity(opportunity_id: uuid.UUID, payload: JobOpportunityUpdate, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    opportunity = update_opportunity(db, user_id=user_id, opportunity_id=opportunity_id, data=payload)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    db.commit()
    return opportunity
