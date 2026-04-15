"""
Recommendation engine — deterministic rules + ML-assisted scoring.

Produces:
- ReorderRecommendation: when stock < reorder_point and forecast demand exceeds cover
- RedistributionRecommendation: when one location has excess and another has shortage
"""
from __future__ import annotations

import json
import uuid
from datetime import date
from typing import NamedTuple

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.logging import log
from app.models.ai import (
    AnomalyEvent, DemandForecast, ForecastRun, OverstockRisk,
    ReorderRecommendation, RedistributionRecommendation, ShortageRisk,
)
from app.models.inventory import (
    InventoryLocation, LeadTimeProfile, ReorderPolicy, StockBalance,
)
from app.models.product import CatalogItem, Product


class EvidenceItem(NamedTuple):
    type: str
    id: str
    label: str
    value: str | None = None


class RecommendationEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, trust_id: uuid.UUID, run_id: uuid.UUID | None = None) -> tuple[int, int]:
        """Return (reorder_count, redistribution_count)."""
        # Use latest completed run if not specified
        if run_id is None:
            latest = self.db.scalar(
                select(ForecastRun)
                .where(ForecastRun.trust_id == trust_id, ForecastRun.status == "completed")
                .order_by(ForecastRun.created_at.desc())
            )
            if not latest:
                log.warning("no_completed_forecast_run", trust_id=str(trust_id))
                return 0, 0
            run_id = latest.id

        reorder_n = self._generate_reorder_recommendations(trust_id, run_id)
        redist_n = self._generate_redistribution_recommendations(trust_id, run_id)
        self.db.commit()
        return reorder_n, redist_n

    # ── Reorder recommendations ───────────────────────────────────────────────

    def _generate_reorder_recommendations(self, trust_id: uuid.UUID, run_id: uuid.UUID) -> int:
        # Get shortage risks above threshold for this run
        stmt = (
            select(ShortageRisk, InventoryLocation, Product, ReorderPolicy, StockBalance)
            .join(InventoryLocation, ShortageRisk.location_id == InventoryLocation.id)
            .join(Product, ShortageRisk.product_id == Product.id)
            .outerjoin(ReorderPolicy, and_(
                ReorderPolicy.location_id == ShortageRisk.location_id,
                ReorderPolicy.product_id == ShortageRisk.product_id,
            ))
            .outerjoin(StockBalance, and_(
                StockBalance.location_id == ShortageRisk.location_id,
                StockBalance.product_id == ShortageRisk.product_id,
            ))
            .where(
                ShortageRisk.run_id == run_id,
                ShortageRisk.trust_id == trust_id,
                ShortageRisk.risk_score >= 0.4,
            )
        )
        rows = self.db.execute(stmt).all()
        count = 0

        for risk, location, product, policy, balance in rows:
            # Skip if recent pending recommendation already exists
            existing = self.db.scalar(
                select(ReorderRecommendation).where(
                    ReorderRecommendation.location_id == risk.location_id,
                    ReorderRecommendation.product_id == risk.product_id,
                    ReorderRecommendation.review_status == "pending",
                )
            )
            if existing:
                continue

            quantity = self._calculate_reorder_quantity(
                risk, policy, balance
            )
            urgency = "urgent" if risk.risk_score >= 0.75 else "normal"
            evidence = self._build_shortage_evidence(risk, balance, policy)
            rationale = self._build_reorder_rationale(risk, balance, policy, product)

            rec = ReorderRecommendation(
                trust_id=trust_id,
                run_id=run_id,
                location_id=risk.location_id,
                product_id=risk.product_id,
                suggested_quantity=quantity,
                urgency=urgency,
                rationale=rationale,
                evidence_json=json.dumps([e._asdict() for e in evidence]),
                review_status="pending",
                confidence=risk.risk_score,
            )
            self.db.add(rec)
            count += 1

        self.db.flush()
        return count

    def _calculate_reorder_quantity(
        self,
        risk: ShortageRisk,
        policy: ReorderPolicy | None,
        balance: StockBalance | None,
    ) -> int:
        current = balance.quantity_on_hand if balance else 0
        if policy:
            # Order up to max_stock, minimum reorder_quantity
            qty = max(policy.reorder_quantity, policy.max_stock - current)
        else:
            # Default: enough for 30 days at forecast daily rate + safety stock
            daily_rate = risk.forecast_demand / max(risk.horizon_days, 1)
            safety_stock = daily_rate * risk.lead_time_days * 1.5
            qty = int((daily_rate * 30) + safety_stock - current)
        return max(1, qty)

    def _build_shortage_evidence(
        self, risk: ShortageRisk, balance: StockBalance | None, policy: ReorderPolicy | None
    ) -> list[EvidenceItem]:
        evidence = [
            EvidenceItem("shortage_risk", str(risk.id), "Shortage risk score",
                        f"{risk.risk_score:.2f}"),
            EvidenceItem("stock_balance", str(balance.id) if balance else "none",
                        "Current stock", str(risk.current_stock)),
            EvidenceItem("forecast", "run_" + str(risk.run_id),
                        f"Forecast demand ({risk.horizon_days}d)", str(risk.forecast_demand)),
            EvidenceItem("lead_time", "profile", "Lead time (days)", str(risk.lead_time_days)),
        ]
        if policy:
            evidence.append(EvidenceItem("policy", str(policy.id), "Reorder point",
                                        str(policy.reorder_point)))
        return evidence

    def _build_reorder_rationale(
        self, risk: ShortageRisk, balance: StockBalance | None,
        policy: ReorderPolicy | None, product: Product
    ) -> str:
        current = balance.quantity_on_hand if balance else 0
        daily_rate = risk.forecast_demand / max(risk.horizon_days, 1)
        days_cover = current / max(daily_rate, 0.01)
        reason_codes = json.loads(risk.reason_codes) if risk.reason_codes else []
        return (
            f"{product.name} at this location has {current} units on hand "
            f"({days_cover:.1f} days cover at current usage rate of {daily_rate:.1f}/day). "
            f"Lead time is {risk.lead_time_days:.0f} days. "
            f"Risk factors: {', '.join(reason_codes) or 'elevated shortage probability'}. "
            f"Risk score: {risk.risk_score:.2f}/1.00."
        )

    # ── Redistribution recommendations ───────────────────────────────────────

    def _generate_redistribution_recommendations(self, trust_id: uuid.UUID, run_id: uuid.UUID) -> int:
        # Shortage locations
        shortage_stmt = (
            select(ShortageRisk)
            .where(
                ShortageRisk.run_id == run_id,
                ShortageRisk.trust_id == trust_id,
                ShortageRisk.risk_score >= 0.5,
            )
        )
        shortages = self.db.scalars(shortage_stmt).all()

        # Overstock locations
        overstock_stmt = (
            select(OverstockRisk)
            .where(
                OverstockRisk.run_id == run_id,
                OverstockRisk.trust_id == trust_id,
                OverstockRisk.excess_quantity > 0,
            )
        )
        overstocks = {
            (str(o.location_id), str(o.product_id)): o
            for o in self.db.scalars(overstock_stmt).all()
        }

        count = 0
        for shortage in shortages:
            key = (str(shortage.location_id), str(shortage.product_id))
            # Find different location with same product and excess
            donor = next(
                (v for k, v in overstocks.items()
                 if k[1] == str(shortage.product_id) and k[0] != str(shortage.location_id)),
                None,
            )
            if not donor:
                continue

            # Don't duplicate
            existing = self.db.scalar(
                select(RedistributionRecommendation).where(
                    RedistributionRecommendation.product_id == shortage.product_id,
                    RedistributionRecommendation.source_location_id == donor.location_id,
                    RedistributionRecommendation.target_location_id == shortage.location_id,
                    RedistributionRecommendation.review_status == "pending",
                )
            )
            if existing:
                continue

            qty = min(donor.excess_quantity, shortage.current_stock + int(shortage.forecast_demand))
            evidence = [
                EvidenceItem("shortage_risk", str(shortage.id), "Target shortage risk",
                            f"{shortage.risk_score:.2f}"),
                EvidenceItem("overstock_risk", str(donor.id), "Source excess quantity",
                            str(donor.excess_quantity)),
                EvidenceItem("stock_balance", "target", "Target current stock",
                            str(shortage.current_stock)),
            ]
            rationale = (
                f"Product has {donor.excess_quantity} excess units at source location "
                f"and shortage risk {shortage.risk_score:.2f} at target location. "
                f"Redistributing {qty} units eliminates excess while reducing shortage risk."
            )

            rec = RedistributionRecommendation(
                trust_id=trust_id,
                run_id=run_id,
                product_id=shortage.product_id,
                source_location_id=donor.location_id,
                target_location_id=shortage.location_id,
                suggested_quantity=qty,
                urgency="urgent" if shortage.risk_score >= 0.75 else "normal",
                rationale=rationale,
                evidence_json=json.dumps([e._asdict() for e in evidence]),
                review_status="pending",
                confidence=min(shortage.risk_score, 0.9),
            )
            self.db.add(rec)
            count += 1

        self.db.flush()
        return count
