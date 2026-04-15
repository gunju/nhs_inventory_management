from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class EvidenceRef(BaseModel):
    type: str  # stock_balance / forecast / lead_time / policy / anomaly
    id: str
    label: str
    value: str | None = None


class ReorderRecommendationOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str | None = None
    location_id: uuid.UUID
    location_name: str | None = None
    suggested_quantity: int
    urgency: str
    confidence: float
    rationale: str | None = None
    evidence: list[EvidenceRef] = []
    review_status: str
    created_at: str

    model_config = {"from_attributes": True}


class RedistributionRecommendationOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str | None = None
    source_location_id: uuid.UUID
    target_location_id: uuid.UUID
    suggested_quantity: int
    urgency: str
    confidence: float
    rationale: str | None = None
    evidence: list[EvidenceRef] = []
    review_status: str
    created_at: str

    model_config = {"from_attributes": True}


class RecommendationRunRequest(BaseModel):
    run_id: uuid.UUID | None = None  # optional: use specific forecast run


class DecisionRequest(BaseModel):
    decision: Literal["approved", "rejected", "snoozed"]
    rationale: str | None = None
    snooze_until: str | None = None  # ISO date
