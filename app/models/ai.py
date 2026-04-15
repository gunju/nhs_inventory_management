"""
AI / analytics models: forecasts, risks, recommendations, anomalies, summaries.
Every recommendation links to structured evidence — no free-text-only decisions.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin, UUIDMixin


class ForecastRun(Base, UUIDMixin, TimestampMixin):
    """Metadata for a batch forecasting run."""
    __tablename__ = "forecast_runs"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    triggered_by_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    run_type: Mapped[str] = mapped_column(String(50), default="scheduled")  # scheduled / manual / api
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # moving_average / exp_smoothing / lightgbm
    horizon_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending / running / completed / failed
    products_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    forecasts: Mapped[list["DemandForecast"]] = relationship(back_populates="run")


class DemandForecast(Base, UUIDMixin, TimestampMixin):
    """Daily demand forecast per product-location."""
    __tablename__ = "demand_forecasts"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("forecast_runs.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)

    forecast_date: Mapped[str] = mapped_column(String(10), nullable=False)  # ISO date string
    q10: Mapped[float] = mapped_column(Float, nullable=False)
    q50: Mapped[float] = mapped_column(Float, nullable=False)
    q90: Mapped[float] = mapped_column(Float, nullable=False)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    feature_importance_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["ForecastRun"] = relationship(back_populates="forecasts")


class ShortageRisk(Base, UUIDMixin, TimestampMixin):
    """Computed shortage risk per product-location-horizon."""
    __tablename__ = "shortage_risks"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("forecast_runs.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)

    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0–1.0
    days_to_stockout: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    forecast_demand: Mapped[float] = mapped_column(Float, nullable=False)
    lead_time_days: Mapped[float] = mapped_column(Float, nullable=False)
    reason_codes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array


class OverstockRisk(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "overstock_risks"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("forecast_runs.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)

    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    excess_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    excess_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    days_of_cover: Mapped[float] = mapped_column(Float, nullable=False)
    reason_codes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReorderRecommendation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reorder_recommendations"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("forecast_runs.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)

    suggested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    urgency: Mapped[str] = mapped_column(String(20), default="normal")  # urgent / normal / low
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / approved / rejected / snoozed
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    decisions: Mapped[list["RecommendationDecision"]] = relationship(
        "RecommendationDecision",
        primaryjoin="and_(RecommendationDecision.recommendation_id == ReorderRecommendation.id, "
                    "RecommendationDecision.recommendation_type == 'reorder')",
        foreign_keys="RecommendationDecision.recommendation_id",
        overlaps="redistribution_decisions",
    )


class RedistributionRecommendation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "redistribution_recommendations"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("forecast_runs.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    source_location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    target_location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)

    suggested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), default="normal")
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


class RecommendationDecision(Base, UUIDMixin, TimestampMixin):
    """Human approval/rejection/snooze decision on any recommendation type."""
    __tablename__ = "recommendation_decisions"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    recommendation_type: Mapped[str] = mapped_column(String(30), nullable=False)  # reorder / redistribution / anomaly
    decided_by_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)

    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # approved / rejected / snoozed
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    snooze_until: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ISO date


class AnomalyEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "anomaly_events"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=True, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("products.id"), nullable=True, index=True)

    anomaly_type: Mapped[str] = mapped_column(String(50), nullable=False)  # SPIKE, DROP, EXPIRY, OUTLIER_MOVEMENT
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # high / medium / low
    detected_at: Mapped[str] = mapped_column(String(27), nullable=False)  # ISO datetime string
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class InsightSummary(Base, UUIDMixin, TimestampMixin):
    """LLM-generated operational summaries (daily / weekly / executive)."""
    __tablename__ = "insight_summaries"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)

    summary_type: Mapped[str] = mapped_column(String(50), nullable=False)  # daily_risk / weekly_inefficiency / executive
    period_start: Mapped[str] = mapped_column(String(10), nullable=False)
    period_end: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
