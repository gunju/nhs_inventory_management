"""
Celery application factory.
Workers are started with: celery -A app.workers.celery_app worker --loglevel=info
Beat scheduler: celery -A app.workers.celery_app beat --loglevel=info
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "nhs_inventory",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.forecast_tasks",
        "app.workers.tasks.integration_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ── Scheduled tasks ────────────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    "daily-forecast-run": {
        "task": "app.workers.tasks.forecast_tasks.run_scheduled_forecast",
        "schedule": crontab(hour=2, minute=0),  # 02:00 UTC daily
    },
    "daily-mock-epr-sync": {
        "task": "app.workers.tasks.integration_tasks.run_mock_epr_sync",
        "schedule": crontab(hour=1, minute=0),  # 01:00 UTC daily
    },
}
