"""Inventory query repository — tenant-scoped."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload

from app.models.inventory import (
    ConsumptionHistory, ExpiryBatchLot, InventoryLocation,
    ReorderPolicy, StockBalance, StockMovement,
)
from app.models.product import Product


class InventoryRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_stock_levels(
        self, trust_id: uuid.UUID,
        location_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        below_reorder_only: bool = False,
    ) -> list[tuple[StockBalance, InventoryLocation, Product, ReorderPolicy | None]]:
        stmt = (
            select(StockBalance, InventoryLocation, Product, ReorderPolicy)
            .join(InventoryLocation, StockBalance.location_id == InventoryLocation.id)
            .join(Product, StockBalance.product_id == Product.id)
            .outerjoin(ReorderPolicy, and_(
                ReorderPolicy.location_id == StockBalance.location_id,
                ReorderPolicy.product_id == StockBalance.product_id,
            ))
            .where(
                StockBalance.trust_id == trust_id,
                InventoryLocation.deleted_at.is_(None),
                Product.deleted_at.is_(None),
            )
        )
        if location_id:
            stmt = stmt.where(StockBalance.location_id == location_id)
        if product_id:
            stmt = stmt.where(StockBalance.product_id == product_id)
        rows = self.db.execute(stmt).all()
        if below_reorder_only:
            rows = [
                r for r in rows
                if r[3] and r[0].quantity_on_hand <= r[3].reorder_point
            ]
        return rows

    def get_expiry_risks(
        self, trust_id: uuid.UUID, days_ahead: int = 30
    ) -> list[tuple[ExpiryBatchLot, InventoryLocation, Product]]:
        cutoff = date.today() + timedelta(days=days_ahead)
        stmt = (
            select(ExpiryBatchLot, InventoryLocation, Product)
            .join(InventoryLocation, ExpiryBatchLot.location_id == InventoryLocation.id)
            .join(Product, ExpiryBatchLot.product_id == Product.id)
            .where(
                ExpiryBatchLot.trust_id == trust_id,
                ExpiryBatchLot.expiry_date <= cutoff,
                ExpiryBatchLot.quantity > 0,
                ExpiryBatchLot.is_quarantined == False,  # noqa: E712
            )
            .order_by(ExpiryBatchLot.expiry_date)
        )
        return self.db.execute(stmt).all()

    def get_movements(
        self, trust_id: uuid.UUID,
        location_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[list[StockMovement], int]:
        base = select(StockMovement).where(StockMovement.trust_id == trust_id)
        if location_id:
            base = base.where(StockMovement.location_id == location_id)
        if product_id:
            base = base.where(StockMovement.product_id == product_id)
        if from_date:
            base = base.where(StockMovement.movement_date >= from_date)
        if to_date:
            base = base.where(StockMovement.movement_date <= to_date)
        total = len(self.db.execute(base).all())
        rows = self.db.scalars(
            base.order_by(StockMovement.movement_date.desc()).offset(offset).limit(limit)
        ).all()
        return list(rows), total

    def get_consumption_history(
        self, trust_id: uuid.UUID,
        location_id: uuid.UUID,
        product_id: uuid.UUID,
        days: int = 90,
    ) -> list[ConsumptionHistory]:
        from_date = date.today() - timedelta(days=days)
        stmt = (
            select(ConsumptionHistory)
            .where(
                ConsumptionHistory.trust_id == trust_id,
                ConsumptionHistory.location_id == location_id,
                ConsumptionHistory.product_id == product_id,
                ConsumptionHistory.consumption_date >= from_date,
            )
            .order_by(ConsumptionHistory.consumption_date)
        )
        return list(self.db.scalars(stmt).all())

    def upsert_stock_balance(
        self, trust_id: uuid.UUID,
        location_id: uuid.UUID,
        product_id: uuid.UUID,
        qty_on_hand: int,
        balance_as_of: date,
    ) -> StockBalance:
        from datetime import datetime, timezone
        stmt = select(StockBalance).where(
            StockBalance.location_id == location_id,
            StockBalance.product_id == product_id,
        )
        balance = self.db.scalar(stmt)
        if balance:
            balance.quantity_on_hand = qty_on_hand
            balance.balance_as_of = datetime.combine(balance_as_of, datetime.min.time()).replace(tzinfo=timezone.utc)
            balance.version += 1
        else:
            balance = StockBalance(
                trust_id=trust_id,
                location_id=location_id,
                product_id=product_id,
                quantity_on_hand=qty_on_hand,
                balance_as_of=datetime.combine(balance_as_of, datetime.min.time()).replace(tzinfo=timezone.utc),
            )
            self.db.add(balance)
        self.db.flush()
        return balance
