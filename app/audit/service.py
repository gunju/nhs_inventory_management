"""
Audit service — append-only logging of actions, data access, and model decisions.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog, DataAccessLog, ModelDecisionLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log_action(
        self,
        action: str,
        trust_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        outcome: str = "success",
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        from app.api.middleware.request_id import get_request_id
        entry = AuditLog(
            trust_id=trust_id,
            user_id=user_id,
            request_id=request_id or get_request_id(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            ip_address=ip_address,
            details_json=json.dumps(details) if details else None,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def log_data_access(
        self,
        endpoint: str,
        method: str,
        trust_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        data_classification: str = "operational",
        request_id: str | None = None,
        response_status: int | None = None,
    ) -> DataAccessLog:
        from app.api.middleware.request_id import get_request_id
        entry = DataAccessLog(
            trust_id=trust_id,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            resource_type=resource_type,
            data_classification=data_classification,
            request_id=request_id or get_request_id(),
            response_status=response_status,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def log_model_decision(
        self,
        model_name: str,
        model_version: str,
        input_features: dict[str, Any],
        output: dict[str, Any],
        trust_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        confidence: float | None = None,
        reason_codes: list[str] | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> ModelDecisionLog:
        entry = ModelDecisionLog(
            trust_id=trust_id,
            run_id=run_id,
            model_name=model_name,
            model_version=model_version,
            input_features_json=json.dumps(input_features),
            output_json=json.dumps(output),
            reason_codes=json.dumps(reason_codes) if reason_codes else None,
            confidence=confidence,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self.db.add(entry)
        self.db.flush()
        return entry
