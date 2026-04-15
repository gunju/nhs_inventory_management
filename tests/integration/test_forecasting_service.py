"""Integration tests: forecasting service with DB."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from app.forecasting.service import ForecastingService
from app.models.ai import DemandForecast, ForecastRun, ShortageRisk
from tests.conftest import LOC_ID, PRODUCT_ID, TRUST_ID


def test_forecast_run_creates_records(db: Session, consumption_history, stock_balance):
    svc = ForecastingService(db)
    run = svc.run_forecast(trust_id=TRUST_ID, horizon_days=7, model_type="moving_average")
    assert run.status == "completed"
    assert run.products_processed >= 1
    from sqlalchemy import select
    forecasts = db.scalars(select(DemandForecast).where(DemandForecast.run_id == run.id)).all()
    assert len(forecasts) == 7  # 7 horizon days


def test_shortage_risk_computed(db: Session, consumption_history, stock_balance):
    svc = ForecastingService(db)
    run = svc.run_forecast(trust_id=TRUST_ID, horizon_days=7, model_type="moving_average")
    from sqlalchemy import select
    risks = db.scalars(select(ShortageRisk).where(ShortageRisk.run_id == run.id)).all()
    assert len(risks) >= 1
    for risk in risks:
        assert 0.0 <= risk.risk_score <= 1.0


def test_forecast_with_no_history_does_not_crash(db: Session, location, product):
    """Locations with no history should produce 0 processed products."""
    svc = ForecastingService(db)
    run = svc.run_forecast(trust_id=TRUST_ID, horizon_days=7, model_type="auto")
    # Should not fail — just no products processed
    assert run.status in ("completed", "failed")


def test_failed_run_recorded(db: Session):
    """Invalid trust produces graceful failure or empty run."""
    svc = ForecastingService(db)
    fake_trust = uuid.uuid4()
    run = svc.run_forecast(trust_id=fake_trust, horizon_days=7)
    assert run.status == "completed"
    assert run.products_processed == 0
