from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.copilot import InventoryRecommendationRequest, InventoryRecommendationResponse
from app.services.copilot_service import CopilotService


router = APIRouter()


@router.post("/inventory-recommendation", response_model=InventoryRecommendationResponse)
def recommend_inventory(
    payload: InventoryRecommendationRequest,
    db: Session = Depends(get_db),
) -> InventoryRecommendationResponse:
    service = CopilotService(db)
    return service.run_inventory_copilot(payload)
