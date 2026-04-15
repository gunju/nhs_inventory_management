"""Celery task: scheduled forecast run for all active trusts."""
from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.forecast_tasks.run_scheduled_forecast", bind=True)
def run_scheduled_forecast(self) -> dict:
    from app.db.session import SessionLocal
    from app.forecasting.service import ForecastingService
    from app.models.org import Trust
    from sqlalchemy import select

    db = SessionLocal()
    results = []
    try:
        trusts = db.scalars(select(Trust).where(Trust.is_active == True, Trust.deleted_at.is_(None))).all()  # noqa: E712
        for trust in trusts:
            svc = ForecastingService(db)
            run = svc.run_forecast(trust_id=trust.id, horizon_days=30, model_type="auto")
            results.append({"trust_id": str(trust.id), "run_id": str(run.id), "status": run.status})
    finally:
        db.close()
    return {"runs": results}


@celery_app.task(name="app.workers.tasks.forecast_tasks.run_forecast_for_trust")
def run_forecast_for_trust(trust_id: str, horizon_days: int = 30, model_type: str = "auto") -> dict:
    import uuid
    from app.db.session import SessionLocal
    from app.forecasting.service import ForecastingService

    db = SessionLocal()
    try:
        svc = ForecastingService(db)
        run = svc.run_forecast(uuid.UUID(trust_id), horizon_days=horizon_days, model_type=model_type)
        return {"run_id": str(run.id), "status": run.status, "count": run.products_processed}
    finally:
        db.close()
