from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.referral import ReferralDraftResponse
from app.services.referral_service import ReferralService


router = APIRouter()


@router.get("/draft", response_model=ReferralDraftResponse)
def build_referral_draft(
    patient_pseudo_id: str = Query(...),
    specialty_requested: str = Query("respiratory"),
    db: Session = Depends(get_db),
) -> ReferralDraftResponse:
    service = ReferralService(db)
    return service.build_draft(patient_pseudo_id, specialty_requested)
