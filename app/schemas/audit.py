from __future__ import annotations

import uuid

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    trust_id: uuid.UUID | None
    user_id: uuid.UUID | None
    request_id: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    outcome: str
    created_at: str

    model_config = {"from_attributes": True}


class IntegrationRunOut(BaseModel):
    id: uuid.UUID
    adapter_name: str
    status: str
    records_ingested: int
    records_failed: int
    error_message: str | None
    started_at: str | None
    finished_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


class ModelDecisionLogOut(BaseModel):
    id: uuid.UUID
    model_name: str
    model_version: str
    confidence: float | None
    reason_codes: str | None
    resource_type: str | None
    resource_id: str | None
    created_at: str

    model_config = {"from_attributes": True}
