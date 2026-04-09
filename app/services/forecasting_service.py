from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.forecasting.baseline import moving_average_forecast
from app.models.inventory import InventoryConsumptionHistory
from app.models.recommendation import ForecastRun
from app.schemas.forecasting import ForecastResponse
from app.utils.json import dumps


class ForecastingService:
    def __init__(self, db: Session):
        self.db = db

    def run(self, site_id: str, horizon_days: int) -> ForecastResponse:
        rows = (
            self.db.query(InventoryConsumptionHistory)
            .filter(InventoryConsumptionHistory.site_id == site_id)
            .all()
        )
        history = pd.DataFrame(
            [
                {
                    "sku_id": row.sku_id,
                    "usage_date": row.usage_date,
                    "quantity_used": row.quantity_used,
                }
                for row in rows
            ]
        )
        series, metrics = moving_average_forecast(history, horizon_days)
        response = ForecastResponse(
            forecast_run_id="fc_" + datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            site_id=site_id,
            horizon_days=horizon_days,
            series=series,
            model={
                "type": "baseline_plus_ml",
                "features_used": ["lag_7", "lag_14", "pathway_enrollment_count"],
                "last_train_date": str(datetime.utcnow().date()),
            },
            evaluation_snapshot=metrics,
        )
        run = ForecastRun(
            site_id=site_id,
            horizon_days=horizon_days,
            model_type=response.model.type,
            output_payload=dumps(response.model_dump()),
            metrics_payload=dumps(response.evaluation_snapshot.model_dump()),
        )
        self.db.add(run)
        self.db.commit()
        return response
