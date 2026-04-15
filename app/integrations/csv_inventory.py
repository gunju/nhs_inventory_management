"""
CSV Inventory Adapter — ingests stock balance CSV files.

Expected CSV columns:
  location_name, product_sku, quantity_on_hand, balance_date (YYYY-MM-DD)
  Optional: quantity_on_order, batch_number, expiry_date
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.base import AdapterResult, BaseAdapter
from app.models.audit import IntegrationRun
from app.models.inventory import (
    ConsumptionHistory, ExpiryBatchLot, InventoryLocation, StockBalance, StockMovement,
)
from app.models.product import Product
from app.repositories.inventory_repo import InventoryRepo


class CSVInventoryAdapter(BaseAdapter):
    adapter_name = "csv_inventory"

    def validate(self, raw_data: Any) -> bool:
        if not raw_data:
            return False
        required = {"location_name", "product_sku", "quantity_on_hand", "balance_date"}
        if isinstance(raw_data, list) and raw_data:
            return required.issubset(set(raw_data[0].keys()))
        return False

    def fetch(self, source_ref: str | None = None) -> list[dict[str, Any]]:
        """source_ref: file path to CSV."""
        if not source_ref:
            return []
        with open(source_ref, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def fetch_from_content(self, content: str) -> list[dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)

    def normalize(self, raw_data: Any) -> list[dict[str, Any]]:
        records = []
        for row in raw_data:
            try:
                records.append({
                    "location_name": str(row["location_name"]).strip(),
                    "product_sku": str(row["product_sku"]).strip().upper(),
                    "quantity_on_hand": int(row["quantity_on_hand"]),
                    "balance_date": date.fromisoformat(str(row["balance_date"]).strip()),
                    "quantity_on_order": int(row.get("quantity_on_order", 0) or 0),
                    "batch_number": row.get("batch_number") or None,
                    "expiry_date": (
                        date.fromisoformat(str(row["expiry_date"]).strip())
                        if row.get("expiry_date") else None
                    ),
                    "_raw": dict(row),
                })
            except (ValueError, KeyError) as exc:
                # Handled in upsert
                records.append({"_error": str(exc), "_raw": dict(row)})
        return records

    def upsert(self, records: list[dict[str, Any]], run: IntegrationRun) -> AdapterResult:
        result = AdapterResult()
        repo = InventoryRepo(self.db)

        for idx, rec in enumerate(records):
            if "_error" in rec:
                result.add_error(idx, str(rec.get("_raw", "")), rec["_error"])
                continue
            try:
                # Resolve location
                location = self.db.scalar(
                    select(InventoryLocation).where(
                        InventoryLocation.trust_id == self.trust_id,
                        InventoryLocation.name == rec["location_name"],
                        InventoryLocation.deleted_at.is_(None),
                    )
                )
                if not location:
                    result.add_error(idx, str(rec["_raw"]),
                                     f"Location not found: {rec['location_name']}")
                    continue

                # Resolve product
                product = self.db.scalar(
                    select(Product).where(
                        Product.sku == rec["product_sku"],
                        Product.deleted_at.is_(None),
                    )
                )
                if not product:
                    result.add_error(idx, str(rec["_raw"]),
                                     f"Product SKU not found: {rec['product_sku']}")
                    continue

                # Upsert stock balance
                balance = repo.upsert_stock_balance(
                    trust_id=self.trust_id,
                    location_id=location.id,
                    product_id=product.id,
                    qty_on_hand=rec["quantity_on_hand"],
                    balance_as_of=rec["balance_date"],
                )

                # Record movement
                movement = StockMovement(
                    trust_id=self.trust_id,
                    location_id=location.id,
                    product_id=product.id,
                    movement_type="BALANCE_SYNC",
                    quantity=rec["quantity_on_hand"],
                    movement_date=rec["balance_date"],
                    reference_id=f"run_{run.id}",
                    source_payload=str(rec["_raw"])[:2000],
                )
                self.db.add(movement)

                # Expiry batch
                if rec.get("batch_number") and rec.get("expiry_date"):
                    existing_lot = self.db.scalar(
                        select(ExpiryBatchLot).where(
                            ExpiryBatchLot.location_id == location.id,
                            ExpiryBatchLot.product_id == product.id,
                            ExpiryBatchLot.batch_number == rec["batch_number"],
                        )
                    )
                    if existing_lot:
                        existing_lot.quantity = rec["quantity_on_hand"]
                        existing_lot.expiry_date = rec["expiry_date"]
                    else:
                        lot = ExpiryBatchLot(
                            trust_id=self.trust_id,
                            location_id=location.id,
                            product_id=product.id,
                            batch_number=rec["batch_number"],
                            quantity=rec["quantity_on_hand"],
                            expiry_date=rec["expiry_date"],
                            receipt_date=rec["balance_date"],
                        )
                        self.db.add(lot)

                result.ingested += 1
            except Exception as exc:
                result.add_error(idx, str(rec.get("_raw", "")), str(exc))

        self.db.flush()
        return result
