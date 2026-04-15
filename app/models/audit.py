"""
Audit, governance, and integration tracking models.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, GUID, TimestampMixin, UUIDMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Append-only log of all significant system actions."""
    __tablename__ = "audit_logs"

    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), default="success")  # success / failure
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class DataAccessLog(Base, UUIDMixin, TimestampMixin):
    """Data access log for DSPT evidence — who accessed what data."""
    __tablename__ = "data_access_logs"

    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_classification: Mapped[str] = mapped_column(String(50), default="operational")  # operational / pii_adjacent / clinical
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)


class IntegrationRun(Base, UUIDMixin, TimestampMixin):
    """Record of each adapter/integration execution."""
    __tablename__ = "integration_runs"

    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)

    adapter_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending / running / completed / failed / partial
    records_ingested: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(27), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(27), nullable=True)


class FailedIntegrationEvent(Base, UUIDMixin, TimestampMixin):
    """Individual failed rows from an integration run — for triage queue."""
    __tablename__ = "failed_integration_events"

    run_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("integration_runs.id"), nullable=False, index=True)
    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)

    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class ModelDecisionLog(Base, UUIDMixin, TimestampMixin):
    """AI/ML model decision trace — links model outputs to their inputs/features."""
    __tablename__ = "model_decision_logs"

    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_features_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_json: Mapped[str] = mapped_column(Text, nullable=False)
    reason_codes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class PromptTemplateVersion(Base, UUIDMixin, TimestampMixin):
    """Versioned prompt templates — ensures reproducibility and auditability."""
    __tablename__ = "prompt_template_versions"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
