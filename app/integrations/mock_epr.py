"""
Mock EPR Activity Adapter — simulates ward activity data from an EPR system.
Generates synthetic consumption events for forecasting.
"""
from __future__ import annotations

import random
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.base import AdapterResult, BaseAdapter
from app.models.audit import IntegrationRun
from app.models.inventory import ConsumptionHistory, InventoryLocation, StockBalance
from app.models.product import Product


class MockEPRActivityAdapter(BaseAdapter):
    adapter_name = "mock_epr_activity"

    def validate(self, raw_data: Any) -> bool:
        return isinstance(raw_data, list)

    def fetch(self, source_ref: str | None = None) -> list[dict[str, Any]]:
        """Generate synthetic activity data for all product-location pairs."""
        stmt = (
            select(StockBalance.location_id, StockBalance.product_id)
            .where(StockBalance.trust_id == self.trust_id)
        )
        pairs = self.db.execute(stmt).all()
        records = []
        today = date.today()
        rng = random.Random(42)  # deterministic seed

        for loc_id, prod_id in pairs:
            product = self.db.get(Product, prod_id)
            base_usage = rng.randint(2, 25)
            for days_back in range(1, 8):  # last 7 days
            	activity_date = today - timedelta(days=days_back)
            	# weekend dip
            	multiplier = 0.6 if activity_date.weekday() >= 5 else 1.0
            	qty = max(0, int(base_usage * multiplier * rng.gauss(1.0, 0.2)))
            	records.append({
                    "location_id": str(loc_id),
                    "product_id": str(prod_id),
                    "activity_date": activity_date.isoformat(),
                    "quantity_consumed": qty,
                    "source": "mock_epr",
            	})
        return records

    def normalize(self, raw_data: Any) -> list[dict[str, Any]]:
        return raw_data  # already normalised

    def upsert(self, records: list[dict[str, Any]], run: IntegrationRun) -> AdapterResult:
        result = AdapterResult()
        for idx, rec in enumerate(records):
            try:
                loc_id = uuid.UUID(rec["location_id"])
                prod_id = uuid.UUID(rec["product_id"])
                activity_date = date.fromisoformat(rec["activity_date"])

                existing = self.db.scalar(
                    select(ConsumptionHistory).where(
                        ConsumptionHistory.location_id == loc_id,
                        ConsumptionHistory.product_id == prod_id,
                        ConsumptionHistory.consumption_date == activity_date,
                    )
                )
                if existing:
                    existing.quantity_consumed = rec["quantity_consumed"]
                else:
                    ch = ConsumptionHistory(
                        trust_id=self.trust_id,
                        location_id=loc_id,
                        product_id=prod_id,
                        consumption_date=activity_date,
                        quantity_consumed=rec["quantity_consumed"],
                        data_source="mock_epr",
                    )
                    self.db.add(ch)
                result.ingested += 1
            except Exception as exc:
                result.add_error(idx, str(rec), str(exc))
        self.db.flush()
        return result
