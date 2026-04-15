"""Celery task: run integration adapters."""
from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.integration_tasks.run_mock_epr_sync")
def run_mock_epr_sync() -> dict:
    from app.db.session import SessionLocal
    from app.integrations.mock_epr import MockEPRActivityAdapter
    from app.models.org import Trust
    from sqlalchemy import select

    db = SessionLocal()
    results = []
    try:
        trusts = db.scalars(select(Trust).where(Trust.is_active == True, Trust.deleted_at.is_(None))).all()  # noqa: E712
        for trust in trusts:
            adapter = MockEPRActivityAdapter(db, trust.id)
            run = adapter.run()
            results.append({
                "trust_id": str(trust.id),
                "run_id": str(run.id),
                "status": run.status,
                "ingested": run.records_ingested,
            })
    finally:
        db.close()
    return {"runs": results}


@celery_app.task(name="app.workers.tasks.integration_tasks.run_adapter")
def run_adapter(adapter_name: str, trust_id: str, source_ref: str | None = None) -> dict:
    import uuid
    from app.db.session import SessionLocal
    from app.integrations.registry import get_adapter

    db = SessionLocal()
    try:
        adapter_cls = get_adapter(adapter_name)
        adapter = adapter_cls(db, uuid.UUID(trust_id))
        run = adapter.run(source_ref=source_ref)
        return {"run_id": str(run.id), "status": run.status}
    finally:
        db.close()
