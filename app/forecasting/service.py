"""
Forecasting service — orchestrates run creation, model selection, shortage/overstock scoring.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import log
from app.forecasting.models import ForecastResult, select_best_model
from app.models.ai import (
    DemandForecast, ForecastRun, OverstockRisk, ShortageRisk,
)
from app.models.inventory import (
    ConsumptionHistory, InventoryLocation, ReorderPolicy, StockBalance,
)
from app.models.product import Product


class ForecastingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run_forecast(
        self,
        trust_id: uuid.UUID,
        horizon_days: int = 30,
        model_type: str = "auto",
        location_ids: list[uuid.UUID] | None = None,
        product_ids: list[uuid.UUID] | None = None,
        triggered_by_id: uuid.UUID | None = None,
    ) -> ForecastRun:
        run = ForecastRun(
            trust_id=trust_id,
            triggered_by_id=triggered_by_id,
            run_type="manual" if triggered_by_id else "api",
            model_type=model_type,
            horizon_days=horizon_days,
            status="running",
        )
        self.db.add(run)
        self.db.flush()

        try:
            count = self._execute_run(run, trust_id, horizon_days, model_type, location_ids, product_ids)
            run.products_processed = count
            run.status = "completed"
            log.info("forecast_run_complete", run_id=str(run.id), count=count)
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            log.error("forecast_run_failed", run_id=str(run.id), error=str(exc))

        self.db.commit()
        return run

    def _execute_run(
        self, run: ForecastRun, trust_id: uuid.UUID,
        horizon_days: int, model_type: str,
        location_ids: list[uuid.UUID] | None,
        product_ids: list[uuid.UUID] | None,
    ) -> int:
        # Get all product-location pairs with consumption history
        stmt = (
            select(ConsumptionHistory.location_id, ConsumptionHistory.product_id)
            .where(ConsumptionHistory.trust_id == trust_id)
            .distinct()
        )
        if location_ids:
            stmt = stmt.where(ConsumptionHistory.location_id.in_(location_ids))
        if product_ids:
            stmt = stmt.where(ConsumptionHistory.product_id.in_(product_ids))

        pairs = self.db.execute(stmt).all()
        count = 0

        for loc_id, prod_id in pairs:
            history = self._get_history(trust_id, loc_id, prod_id)
            if history.empty:
                continue

            if model_type == "auto":
                model = select_best_model(history)
            elif model_type == "moving_average":
                from app.forecasting.models import MovingAverageModel
                model = MovingAverageModel()
            elif model_type == "exp_smoothing":
                from app.forecasting.models import ExponentialSmoothingModel
                model = ExponentialSmoothingModel()
            else:
                from app.forecasting.models import LightGBMModel
                model = LightGBMModel()

            result = model.fit_predict(history, horizon_days, str(loc_id), str(prod_id))
            self._save_forecast(run, trust_id, loc_id, prod_id, result)
            self._compute_shortage_risk(run, trust_id, loc_id, prod_id, result, horizon_days)
            self._compute_overstock_risk(run, trust_id, loc_id, prod_id, result)
            count += 1

        return count

    def _get_history(self, trust_id: uuid.UUID, location_id: uuid.UUID, product_id: uuid.UUID) -> pd.DataFrame:
        stmt = (
            select(ConsumptionHistory.consumption_date, ConsumptionHistory.quantity_consumed)
            .where(
                ConsumptionHistory.trust_id == trust_id,
                ConsumptionHistory.location_id == location_id,
                ConsumptionHistory.product_id == product_id,
            )
            .order_by(ConsumptionHistory.consumption_date)
        )
        rows = self.db.execute(stmt).all()
        if not rows:
            return pd.DataFrame(columns=["consumption_date", "quantity_consumed"])
        return pd.DataFrame(rows, columns=["consumption_date", "quantity_consumed"])

    def _save_forecast(
        self, run: ForecastRun, trust_id: uuid.UUID,
        location_id: uuid.UUID, product_id: uuid.UUID,
        result: ForecastResult,
    ) -> None:
        for pt in result.points:
            forecast = DemandForecast(
                trust_id=trust_id,
                run_id=run.id,
                location_id=location_id,
                product_id=product_id,
                forecast_date=pt.forecast_date.isoformat(),
                q10=pt.q10,
                q50=pt.q50,
                q90=pt.q90,
                model_used=result.model_used,
                confidence=result.confidence,
                feature_importance_json=json.dumps(result.feature_importance) if result.feature_importance else None,
            )
            self.db.add(forecast)
        self.db.flush()

    def _compute_shortage_risk(
        self, run: ForecastRun, trust_id: uuid.UUID,
        location_id: uuid.UUID, product_id: uuid.UUID,
        result: ForecastResult, horizon_days: int,
    ) -> None:
        # Get current stock
        balance = self.db.scalar(
            select(StockBalance).where(
                StockBalance.location_id == location_id,
                StockBalance.product_id == product_id,
            )
        )
        current_stock = balance.quantity_on_hand if balance else 0

        # Lead time
        from app.models.inventory import LeadTimeProfile
        lt = self.db.scalar(
            select(LeadTimeProfile).where(
                LeadTimeProfile.trust_id == trust_id,
                LeadTimeProfile.product_id == product_id,
            )
        )
        lead_time = float(lt.mean_days) if lt else 7.0

        # Total forecast demand
        total_demand_q50 = sum(pt.q50 for pt in result.points)
        total_demand_q90 = sum(pt.q90 for pt in result.points)

        # Days to stockout
        daily_avg = total_demand_q50 / max(horizon_days, 1)
        days_to_stockout = current_stock / max(daily_avg, 0.01)

        # Risk score: probability of hitting zero within lead time window
        # Simple heuristic: 1 - (current_stock / (demand_in_lead_time + 1))
        demand_in_lead_time = daily_avg * lead_time
        risk_score = min(1.0, max(0.0, 1.0 - (current_stock / max(demand_in_lead_time * 1.5, 1.0))))

        reason_codes = []
        if current_stock == 0:
            reason_codes.append("ZERO_STOCK")
        if days_to_stockout < lead_time:
            reason_codes.append("INSUFFICIENT_COVER_FOR_LEAD_TIME")
        if total_demand_q90 > current_stock * 1.5:
            reason_codes.append("HIGH_DEMAND_FORECAST")

        risk = ShortageRisk(
            trust_id=trust_id,
            run_id=run.id,
            location_id=location_id,
            product_id=product_id,
            horizon_days=horizon_days,
            risk_score=risk_score,
            days_to_stockout=round(days_to_stockout, 1),
            current_stock=current_stock,
            forecast_demand=round(total_demand_q50, 1),
            lead_time_days=lead_time,
            reason_codes=json.dumps(reason_codes),
        )
        self.db.add(risk)
        self.db.flush()

    def _compute_overstock_risk(
        self, run: ForecastRun, trust_id: uuid.UUID,
        location_id: uuid.UUID, product_id: uuid.UUID,
        result: ForecastResult,
    ) -> None:
        policy = self.db.scalar(
            select(ReorderPolicy).where(
                ReorderPolicy.location_id == location_id,
                ReorderPolicy.product_id == product_id,
            )
        )
        balance = self.db.scalar(
            select(StockBalance).where(
                StockBalance.location_id == location_id,
                StockBalance.product_id == product_id,
            )
        )
        current_stock = balance.quantity_on_hand if balance else 0
        max_stock = policy.max_stock if policy else current_stock * 2

        daily_avg = sum(pt.q50 for pt in result.points) / max(len(result.points), 1)
        days_of_cover = current_stock / max(daily_avg, 0.01)
        excess = max(0, current_stock - max_stock)

        risk_score = min(1.0, max(0.0, excess / max(max_stock, 1)))

        if risk_score < 0.1 and days_of_cover < 60:
            return  # not worth recording

        # estimate excess value
        from app.models.product import CatalogItem
        catalog = self.db.scalar(
            select(CatalogItem).where(
                CatalogItem.product_id == product_id,
                CatalogItem.is_preferred == True,  # noqa: E712
            )
        )
        unit_price = float(catalog.unit_price) if catalog and catalog.unit_price else None
        excess_value = (unit_price * excess) if unit_price else None

        reason_codes = []
        if excess > 0:
            reason_codes.append("ABOVE_MAX_STOCK")
        if days_of_cover > 90:
            reason_codes.append("HIGH_DAYS_OF_COVER")

        risk = OverstockRisk(
            trust_id=trust_id,
            run_id=run.id,
            location_id=location_id,
            product_id=product_id,
            risk_score=risk_score,
            excess_quantity=excess,
            excess_value=excess_value,
            days_of_cover=round(days_of_cover, 1),
            reason_codes=json.dumps(reason_codes),
        )
        self.db.add(risk)
        self.db.flush()
