from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.forecasting import ForecastResponse
from app.services.forecasting_service import ForecastingService


router = APIRouter()


@router.get("/run", response_model=ForecastResponse)
def run_forecast(
    site_id: str = Query("site_01"),
    horizon_days: int = Query(14),
    db: Session = Depends(get_db),
) -> ForecastResponse:
    service = ForecastingService(db)
    return service.run(site_id=site_id, horizon_days=horizon_days)
