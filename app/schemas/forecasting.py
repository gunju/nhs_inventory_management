from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ForecastRunRequest(BaseModel):
    horizon_days: int = Field(default=30, ge=1, le=90)
    model_type: Literal["auto", "moving_average", "exp_smoothing", "lightgbm"] = "auto"
    location_ids: list[uuid.UUID] | None = None
    product_ids: list[uuid.UUID] | None = None


class ForecastRunOut(BaseModel):
    id: uuid.UUID
    trust_id: uuid.UUID
    run_type: str
    model_type: str
    horizon_days: int
    status: str
    products_processed: int
    error_message: str | None = None
    metrics_json: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class DemandForecastOut(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    product_id: uuid.UUID
    forecast_date: str
    q10: float
    q50: float
    q90: float
    model_used: str
    confidence: float

    model_config = {"from_attributes": True}
