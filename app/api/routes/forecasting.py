"""Forecasting endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.middleware.auth import CurrentUser, require_roles
from app.db.session import get_db
from app.forecasting.service import ForecastingService
from app.models.ai import DemandForecast, ForecastRun
from app.models.user import ROLE_ANALYST, ROLE_SUPPLY_CHAIN_MANAGER
from app.schemas.forecasting import DemandForecastOut, ForecastRunOut, ForecastRunRequest

router = APIRouter()

_ROLES = (ROLE_SUPPLY_CHAIN_MANAGER, ROLE_ANALYST)


@router.post("/run", response_model=ForecastRunOut, summary="Trigger a forecast run")
def run_forecast(
    body: ForecastRunRequest,
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_ROLES)],
    db: Annotated[Session, Depends(get_db)],
) -> ForecastRunOut:
    trust_id = current_user.trust_id
    svc = ForecastingService(db)
    run = svc.run_forecast(
        trust_id=trust_id,
        horizon_days=body.horizon_days,
        model_type=body.model_type,
        location_ids=body.location_ids,
        product_ids=body.product_ids,
        triggered_by_id=current_user.id,
    )
    return ForecastRunOut(
        id=run.id,
        trust_id=run.trust_id,
        run_type=run.run_type,
        model_type=run.model_type,
        horizon_days=run.horizon_days,
        status=run.status,
        products_processed=run.products_processed,
        error_message=run.error_message,
        metrics_json=run.metrics_json,
        created_at=run.created_at.isoformat(),
    )


@router.get("/results", response_model=list[ForecastRunOut], summary="List forecast runs")
def list_runs(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 20,
) -> list[ForecastRunOut]:
    trust_id = current_user.trust_id
    stmt = (
        select(ForecastRun)
        .where(ForecastRun.trust_id == trust_id)
        .order_by(ForecastRun.created_at.desc())
        .limit(limit)
    )
    runs = db.scalars(stmt).all()
    return [
        ForecastRunOut(
            id=r.id, trust_id=r.trust_id, run_type=r.run_type,
            model_type=r.model_type, horizon_days=r.horizon_days,
            status=r.status, products_processed=r.products_processed,
            error_message=r.error_message, metrics_json=r.metrics_json,
            created_at=r.created_at.isoformat(),
        )
        for r in runs
    ]


@router.get("/{run_id}", response_model=list[DemandForecastOut], summary="Forecast results for a run")
def get_run_results(
    run_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    product_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
) -> list[DemandForecastOut]:
    trust_id = current_user.trust_id
    stmt = select(DemandForecast).where(
        DemandForecast.run_id == run_id,
        DemandForecast.trust_id == trust_id,
    )
    if product_id:
        stmt = stmt.where(DemandForecast.product_id == product_id)
    if location_id:
        stmt = stmt.where(DemandForecast.location_id == location_id)

    rows = db.scalars(stmt).all()
    return [
        DemandForecastOut(
            id=r.id, location_id=r.location_id, product_id=r.product_id,
            forecast_date=r.forecast_date, q10=r.q10, q50=r.q50, q90=r.q90,
            model_used=r.model_used, confidence=r.confidence,
        )
        for r in rows
    ]
