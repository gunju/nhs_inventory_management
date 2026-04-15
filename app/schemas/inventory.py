from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class StockLevelOut(BaseModel):
    location_id: uuid.UUID
    location_name: str
    product_id: uuid.UUID
    product_name: str
    sku: str
    quantity_on_hand: int
    quantity_reserved: int
    quantity_on_order: int
    reorder_point: int | None = None
    is_below_reorder: bool = False
    balance_as_of: datetime

    model_config = {"from_attributes": True}


class MovementOut(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    product_id: uuid.UUID
    movement_type: str
    quantity: int
    movement_date: date
    reference_id: str | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


class ExpiryRiskOut(BaseModel):
    location_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    batch_number: str
    expiry_date: date
    quantity: int
    days_to_expiry: int

    model_config = {"from_attributes": True}


class StockoutRiskOut(BaseModel):
    location_id: uuid.UUID
    location_name: str
    product_id: uuid.UUID
    product_name: str
    sku: str
    risk_score: float
    days_to_stockout: float | None
    current_stock: int
    horizon_days: int

    model_config = {"from_attributes": True}


class OverstockRiskOut(BaseModel):
    location_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    risk_score: float
    excess_quantity: int
    excess_value: float | None
    days_of_cover: float

    model_config = {"from_attributes": True}
