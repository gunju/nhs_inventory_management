from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: uuid.UUID | None = None  # None = start new session
    message: str = Field(..., min_length=1, max_length=4000)
    trust_id: uuid.UUID | None = None


class EvidenceRef(BaseModel):
    type: str  # stock_balance / forecast / lead_time / policy / anomaly / document
    id: str
    label: str
    value: str | None = None


class CopilotResponse(BaseModel):
    session_id: uuid.UUID
    answer: str
    confidence: float | None = None
    reason_codes: list[str] = []
    evidence: list[EvidenceRef] = []
    recommended_actions: list[str] = []
    follow_up_questions: list[str] = []
    grounded: bool = True

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str | None = None
    is_active: bool
    created_at: str
    messages: list[dict[str, Any]] = []

    model_config = {"from_attributes": True}
