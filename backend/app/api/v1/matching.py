import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_id
from app.schemas.candidate_profile import CandidateProfileResponse, CandidateProfileUpsert
from app.schemas.job_match import JobMatchResponse
from app.services.job_matching import create_or_refresh_match, get_current_match, get_profile, upsert_profile

router = APIRouter(tags=["Matching"])


@router.get("/candidate-profile", response_model=CandidateProfileResponse)
def read_candidate_profile(user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    profile = get_profile(db, user_id=user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return profile


@router.put("/candidate-profile", response_model=CandidateProfileResponse)
def save_candidate_profile(payload: CandidateProfileUpsert, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    profile = upsert_profile(db, user_id=user_id, data=payload)
    db.commit()
    return profile


@router.post("/opportunities/{opportunity_id}/match", response_model=JobMatchResponse)
def refresh_opportunity_match(opportunity_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    assessment = create_or_refresh_match(db, user_id=user_id, opportunity_id=opportunity_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Opportunity or candidate profile not found")
    db.commit()
    return assessment


@router.get("/opportunities/{opportunity_id}/match", response_model=JobMatchResponse)
def read_opportunity_match(opportunity_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    assessment = get_current_match(db, user_id=user_id, opportunity_id=opportunity_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Current match assessment not found")
    return assessment
