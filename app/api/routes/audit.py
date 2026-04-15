"""Audit, governance, and integration management endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.middleware.auth import CurrentUser, require_roles
from app.core.pagination import PageParams, PagedResponse
from app.db.session import get_db
from app.models.audit import AuditLog, IntegrationRun, ModelDecisionLog, FailedIntegrationEvent
from app.models.user import ROLE_SUPPLY_CHAIN_MANAGER, ROLE_TRUST_ADMIN, ROLE_ANALYST
from app.schemas.audit import AuditLogOut, IntegrationRunOut, ModelDecisionLogOut

router = APIRouter()

_AUDIT_ROLES = (ROLE_TRUST_ADMIN, ROLE_SUPPLY_CHAIN_MANAGER, ROLE_ANALYST)


@router.get("/events", response_model=PagedResponse[AuditLogOut], summary="Audit log events")
def audit_events(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_AUDIT_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    action: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PagedResponse[AuditLogOut]:
    params = PageParams(page=page, page_size=page_size)
    stmt = (
        select(AuditLog)
        .where(AuditLog.trust_id == current_user.trust_id)
        .order_by(AuditLog.created_at.desc())
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    all_rows = db.scalars(stmt).all()
    total = len(all_rows)
    rows = all_rows[params.offset: params.offset + params.page_size]
    items = [
        AuditLogOut(
            id=r.id, trust_id=r.trust_id, user_id=r.user_id,
            request_id=r.request_id, action=r.action,
            resource_type=r.resource_type, resource_id=r.resource_id,
            outcome=r.outcome, created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]
    return PagedResponse.build(items, total, params)


@router.get("/governance/model-decisions", response_model=list[ModelDecisionLogOut])
def model_decisions(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_AUDIT_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ModelDecisionLogOut]:
    stmt = (
        select(ModelDecisionLog)
        .where(ModelDecisionLog.trust_id == current_user.trust_id)
        .order_by(ModelDecisionLog.created_at.desc())
        .limit(limit)
    )
    rows = db.scalars(stmt).all()
    return [
        ModelDecisionLogOut(
            id=r.id, model_name=r.model_name, model_version=r.model_version,
            confidence=r.confidence, reason_codes=r.reason_codes,
            resource_type=r.resource_type, resource_id=r.resource_id,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/integrations/runs", response_model=list[IntegrationRunOut])
def integration_runs(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_AUDIT_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50),
) -> list[IntegrationRunOut]:
    stmt = (
        select(IntegrationRun)
        .where(IntegrationRun.trust_id == current_user.trust_id)
        .order_by(IntegrationRun.created_at.desc())
        .limit(limit)
    )
    rows = db.scalars(stmt).all()
    return [
        IntegrationRunOut(
            id=r.id, adapter_name=r.adapter_name, status=r.status,
            records_ingested=r.records_ingested, records_failed=r.records_failed,
            error_message=r.error_message, started_at=r.started_at,
            finished_at=r.finished_at, created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/integrations/errors", summary="Failed integration events — triage queue")
def integration_errors(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_AUDIT_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50),
) -> list[dict]:
    stmt = (
        select(FailedIntegrationEvent)
        .where(
            FailedIntegrationEvent.trust_id == current_user.trust_id,
            FailedIntegrationEvent.is_resolved == False,  # noqa: E712
        )
        .order_by(FailedIntegrationEvent.created_at.desc())
        .limit(limit)
    )
    rows = db.scalars(stmt).all()
    return [
        {
            "id": str(r.id),
            "run_id": str(r.run_id),
            "row_index": r.row_index,
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
