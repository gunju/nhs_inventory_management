"""
Builds structured context from DB facts for injection into LLM prompts.
Never pass raw patient data or PII — operational inventory facts only.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import AnomalyEvent, ReorderRecommendation, ShortageRisk
from app.models.inventory import (
    ConsumptionHistory, InventoryLocation, ReorderPolicy, StockBalance,
)
from app.models.product import Product


class ContextBuilder:
    def __init__(self, db: Session, trust_id: uuid.UUID) -> None:
        self.db = db
        self.trust_id = trust_id

    def build_for_question(self, question: str) -> tuple[str, list[dict]]:
        """
        Build a grounded context string + evidence refs from the question.
        Returns (context_text, evidence_list).
        """
        evidence: list[dict] = []
        sections: list[str] = []

        question_lower = question.lower()

        # Always include top shortage risks
        shortage_ctx, shortage_ev = self._shortage_context()
        if shortage_ctx:
            sections.append(shortage_ctx)
            evidence.extend(shortage_ev)

        # Include stock levels if question mentions stock / level / how many
        if any(kw in question_lower for kw in ["stock", "level", "quantity", "how many", "units"]):
            stock_ctx, stock_ev = self._stock_levels_context()
            if stock_ctx:
                sections.append(stock_ctx)
                evidence.extend(stock_ev)

        # Include expiry info if question mentions expiry/expire/batch
        if any(kw in question_lower for kw in ["expir", "batch", "waste"]):
            expiry_ctx, expiry_ev = self._expiry_context()
            if expiry_ctx:
                sections.append(expiry_ctx)
                evidence.extend(expiry_ev)

        # Include pending recommendations
        if any(kw in question_lower for kw in ["recommend", "action", "order", "should", "do today"]):
            rec_ctx, rec_ev = self._recommendations_context()
            if rec_ctx:
                sections.append(rec_ctx)
                evidence.extend(rec_ev)

        context = "\n\n".join(sections) if sections else "No inventory data currently available for this trust."
        return context, evidence

    def _shortage_context(self) -> tuple[str, list[dict]]:
        stmt = (
            select(ShortageRisk, InventoryLocation, Product)
            .join(InventoryLocation, ShortageRisk.location_id == InventoryLocation.id)
            .join(Product, ShortageRisk.product_id == Product.id)
            .where(
                ShortageRisk.trust_id == self.trust_id,
                ShortageRisk.risk_score >= 0.4,
            )
            .order_by(ShortageRisk.risk_score.desc())
            .limit(10)
        )
        rows = self.db.execute(stmt).all()
        if not rows:
            return "", []
        lines = ["## Shortage Risks (top 10)"]
        evidence = []
        for risk, loc, prod in rows:
            lines.append(
                f"- {prod.name} (SKU:{prod.sku}) at {loc.name}: "
                f"risk={risk.risk_score:.2f}, current_stock={risk.current_stock}, "
                f"days_to_stockout={risk.days_to_stockout}, "
                f"forecast_demand_{risk.horizon_days}d={risk.forecast_demand:.0f}"
            )
            evidence.append({
                "type": "shortage_risk", "id": str(risk.id),
                "label": f"Shortage risk: {prod.name} @ {loc.name}",
                "value": str(risk.risk_score),
            })
        return "\n".join(lines), evidence

    def _stock_levels_context(self) -> tuple[str, list[dict]]:
        stmt = (
            select(StockBalance, InventoryLocation, Product, ReorderPolicy)
            .join(InventoryLocation, StockBalance.location_id == InventoryLocation.id)
            .join(Product, StockBalance.product_id == Product.id)
            .outerjoin(ReorderPolicy, (
                (ReorderPolicy.location_id == StockBalance.location_id) &
                (ReorderPolicy.product_id == StockBalance.product_id)
            ))
            .where(StockBalance.trust_id == self.trust_id)
            .order_by(StockBalance.quantity_on_hand)
            .limit(20)
        )
        rows = self.db.execute(stmt).all()
        if not rows:
            return "", []
        lines = ["## Current Stock Levels (lowest 20)"]
        evidence = []
        for bal, loc, prod, pol in rows:
            below = ""
            if pol and bal.quantity_on_hand <= pol.reorder_point:
                below = " [BELOW REORDER POINT]"
            lines.append(
                f"- {prod.name} (SKU:{prod.sku}) @ {loc.name}: "
                f"on_hand={bal.quantity_on_hand}, on_order={bal.quantity_on_order}"
                f"{below}"
            )
            evidence.append({
                "type": "stock_balance", "id": str(bal.id),
                "label": f"Stock: {prod.name} @ {loc.name}",
                "value": str(bal.quantity_on_hand),
            })
        return "\n".join(lines), evidence

    def _expiry_context(self) -> tuple[str, list[dict]]:
        from app.models.inventory import ExpiryBatchLot
        cutoff = date.today() + timedelta(days=60)
        stmt = (
            select(ExpiryBatchLot, InventoryLocation, Product)
            .join(InventoryLocation, ExpiryBatchLot.location_id == InventoryLocation.id)
            .join(Product, ExpiryBatchLot.product_id == Product.id)
            .where(
                ExpiryBatchLot.trust_id == self.trust_id,
                ExpiryBatchLot.expiry_date <= cutoff,
                ExpiryBatchLot.quantity > 0,
            )
            .order_by(ExpiryBatchLot.expiry_date)
            .limit(10)
        )
        rows = self.db.execute(stmt).all()
        if not rows:
            return "", []
        today = date.today()
        lines = ["## Expiry Risks (next 60 days)"]
        evidence = []
        for lot, loc, prod in rows:
            days_left = (lot.expiry_date - today).days
            lines.append(
                f"- {prod.name} (SKU:{prod.sku}) batch {lot.batch_number} @ {loc.name}: "
                f"qty={lot.quantity}, expires={lot.expiry_date} ({days_left} days)"
            )
            evidence.append({
                "type": "expiry_batch", "id": str(lot.id),
                "label": f"Expiry: {prod.name} batch {lot.batch_number}",
                "value": str(days_left) + " days",
            })
        return "\n".join(lines), evidence

    def _recommendations_context(self) -> tuple[str, list[dict]]:
        stmt = (
            select(ReorderRecommendation, Product, InventoryLocation)
            .join(Product, ReorderRecommendation.product_id == Product.id)
            .join(InventoryLocation, ReorderRecommendation.location_id == InventoryLocation.id)
            .where(
                ReorderRecommendation.trust_id == self.trust_id,
                ReorderRecommendation.review_status == "pending",
            )
            .order_by(ReorderRecommendation.created_at.desc())
            .limit(5)
        )
        rows = self.db.execute(stmt).all()
        if not rows:
            return "", []
        lines = ["## Pending Reorder Recommendations"]
        evidence = []
        for rec, prod, loc in rows:
            lines.append(
                f"- {prod.name} @ {loc.name}: order {rec.suggested_quantity} units, "
                f"urgency={rec.urgency}, confidence={rec.confidence:.2f}"
            )
            evidence.append({
                "type": "reorder_recommendation", "id": str(rec.id),
                "label": f"Reorder: {prod.name} @ {loc.name}",
                "value": str(rec.suggested_quantity),
            })
        return "\n".join(lines), evidence
