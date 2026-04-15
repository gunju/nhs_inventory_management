"""
BaseAdapter interface — all integration adapters implement this protocol.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import log
from app.models.audit import FailedIntegrationEvent, IntegrationRun


class AdapterResult:
    def __init__(self) -> None:
        self.ingested: int = 0
        self.failed: int = 0
        self.errors: list[dict[str, Any]] = []

    def add_error(self, row_index: int | None, payload: str, error: str) -> None:
        self.failed += 1
        self.errors.append({"row_index": row_index, "payload": payload, "error": error})


class BaseAdapter(ABC):
    adapter_name: str = "base"

    def __init__(self, db: Session, trust_id: uuid.UUID) -> None:
        self.db = db
        self.trust_id = trust_id

    @abstractmethod
    def validate(self, raw_data: Any) -> bool:
        """Return True if data is valid for ingestion."""

    @abstractmethod
    def fetch(self, source_ref: str | None = None) -> Any:
        """Fetch raw data from source."""

    @abstractmethod
    def normalize(self, raw_data: Any) -> list[dict[str, Any]]:
        """Normalise raw records to canonical format."""

    @abstractmethod
    def upsert(self, records: list[dict[str, Any]], run: IntegrationRun) -> AdapterResult:
        """Upsert normalised records into canonical tables."""

    def emit_audit(self, run: IntegrationRun, result: AdapterResult) -> None:
        """Save failed rows to triage queue."""
        for err in result.errors:
            evt = FailedIntegrationEvent(
                run_id=run.id,
                trust_id=self.trust_id,
                row_index=err.get("row_index"),
                raw_payload=str(err.get("payload", ""))[:4000],
                error_message=str(err.get("error", ""))[:2000],
            )
            self.db.add(evt)
        self.db.flush()

    def run(self, source_ref: str | None = None) -> IntegrationRun:
        """Full pipeline: fetch → validate → normalise → upsert → audit."""
        run = IntegrationRun(
            trust_id=self.trust_id,
            adapter_name=self.adapter_name,
            status="running",
            started_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        self.db.add(run)
        self.db.flush()

        try:
            raw = self.fetch(source_ref)
            if not self.validate(raw):
                run.status = "failed"
                run.error_message = "Validation failed"
                self.db.commit()
                return run

            records = self.normalize(raw)
            result = self.upsert(records, run)
            self.emit_audit(run, result)

            run.records_ingested = result.ingested
            run.records_failed = result.failed
            run.status = "completed" if result.failed == 0 else "partial"
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)[:2000]
            log.error("adapter_run_failed", adapter=self.adapter_name, error=str(exc))
        finally:
            run.finished_at = datetime.now(tz=timezone.utc).isoformat()
            self.db.commit()

        return run
