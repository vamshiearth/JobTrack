from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import AuthContext, get_auth_context
from app.models import EmailMessage, ReviewItem
from app.schemas.review_item import ApproveReviewRequest, ReviewDecisionResponse, ReviewEvidenceResponse, ReviewItemListResponse, ReviewItemResponse
from app.services.application_event_service import ApplicationNotFound
from app.services.review_decisions import ReviewConflict, ReviewNotFound, approve_review, reject_review

router = APIRouter(prefix="/review-items", tags=["Review Items"])


def to_response(item: ReviewItem, message: EmailMessage) -> ReviewItemResponse:
    return ReviewItemResponse(id=item.id, status="REJECTED" if item.review_status == "DISMISSED" else item.review_status, category=message.classification_kind, candidate_application_id=item.suggested_application_id, proposed_event_type=item.suggested_event_kind, reasons=[part.strip() for part in item.reason.split(";") if part.strip()], evidence=ReviewEvidenceResponse(sender=message.sender_address, subject=message.subject, received_at=message.received_at), created_at=item.created_at, decided_at=item.resolved_at)


@router.get("", response_model=ReviewItemListResponse)
def list_review_items(status_filter: str = Query("PENDING", alias="status"), page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    query = select(ReviewItem, EmailMessage).join(EmailMessage).where(ReviewItem.user_id == context.user.id, ReviewItem.review_status == ("DISMISSED" if status_filter == "REJECTED" else status_filter))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(ReviewItem.created_at.desc(), ReviewItem.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return ReviewItemListResponse(items=[to_response(item, message) for item, message in rows], total=total, page=page, page_size=page_size)


@router.get("/{review_id}", response_model=ReviewItemResponse)
def get_review_item(review_id: UUID, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    row = db.execute(select(ReviewItem, EmailMessage).join(EmailMessage).where(ReviewItem.id == review_id, ReviewItem.user_id == context.user.id)).first()
    if row is None:
        raise HTTPException(404, "Review item not found")
    return to_response(*row)


@router.post("/{review_id}/approve", response_model=ReviewDecisionResponse)
def approve(review_id: UUID, payload: ApproveReviewRequest, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    try:
        result = approve_review(db, review_id=review_id, user_id=context.user.id, application_id=payload.application_id, interview_round=payload.interview_round)
    except (ReviewNotFound, ApplicationNotFound):
        db.rollback()
        raise HTTPException(404, "Review item or application not found")
    except ReviewConflict as error:
        db.rollback()
        raise HTTPException(409, str(error))
    db.commit()
    return ReviewDecisionResponse(**result.__dict__)


@router.post("/{review_id}/reject", response_model=ReviewDecisionResponse)
def reject(review_id: UUID, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    try:
        result = reject_review(db, review_id=review_id, user_id=context.user.id)
    except ReviewNotFound:
        db.rollback()
        raise HTTPException(404, "Review item not found")
    except ReviewConflict as error:
        db.rollback()
        raise HTTPException(409, str(error))
    db.commit()
    return ReviewDecisionResponse(**result.__dict__)