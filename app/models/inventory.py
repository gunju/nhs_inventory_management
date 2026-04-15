"""
Inventory transaction models: locations, stock, movements, orders, forecasting inputs.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin, UUIDMixin, SoftDeleteMixin, VersionMixin


class InventoryLocation(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Physical or logical location that holds stock."""
    __tablename__ = "inventory_locations"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    hospital_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("hospitals.id"), nullable=False, index=True)
    ward_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("wards.id"), nullable=True, index=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("departments.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[str] = mapped_column(String(50), nullable=False)  # WARD_STORE, MAIN_STORE, THEATRE, PHARMACY
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    stock_balances: Mapped[list["StockBalance"]] = relationship(back_populates="location")


class StockBalance(Base, UUIDMixin, TimestampMixin, VersionMixin):
    """Current stock level for a product at a location."""
    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("location_id", "product_id", name="uq_stock_balance_location_product"),
    )

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)

    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_on_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_movement_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    balance_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    location: Mapped["InventoryLocation"] = relationship(back_populates="stock_balances")


class StockMovement(Base, UUIDMixin, TimestampMixin):
    """Every stock in/out event — append-only ledger."""
    __tablename__ = "stock_movements"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)

    movement_type: Mapped[str] = mapped_column(String(50), nullable=False)  # RECEIPT, ISSUE, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT, EXPIRY_WRITE_OFF
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # positive=in, negative=out
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # PO/GRN/transfer ref
    performed_by_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # raw ingested payload preserved


class StockAdjustment(Base, UUIDMixin, TimestampMixin):
    """Manual stock correction with mandatory reason."""
    __tablename__ = "stock_adjustments"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    adjusted_by_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)

    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    movement_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("stock_movements.id"), nullable=True)


class PurchaseOrder(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "purchase_orders"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False)
    raised_by_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    po_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")  # draft / submitted / approved / received / cancelled
    order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_recommendation_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)

    lines: Mapped[list["PurchaseOrderLine"]] = relationship(back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderLine(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "purchase_order_lines"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("purchase_orders.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("catalog_items.id"), nullable=True)

    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    line_total: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="lines")


class GoodsReceipt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "goods_receipts"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("purchase_orders.id"), nullable=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    received_by_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)

    grn_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TransferOrder(Base, UUIDMixin, TimestampMixin, VersionMixin):
    """Stock transfer between locations within a trust."""
    __tablename__ = "transfer_orders"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    source_location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    target_location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    initiated_by_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending / approved / completed / cancelled
    transfer_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_recommendation_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReorderPolicy(Base, UUIDMixin, TimestampMixin, VersionMixin):
    """Min/max reorder policy for a product-location pair."""
    __tablename__ = "reorder_policies"
    __table_args__ = (
        UniqueConstraint("location_id", "product_id", name="uq_reorder_policy"),
    )

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)

    min_stock: Mapped[int] = mapped_column(Integer, default=0)
    max_stock: Mapped[int] = mapped_column(Integer, default=100)
    reorder_point: Mapped[int] = mapped_column(Integer, default=10)
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=50)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LeadTimeProfile(Base, UUIDMixin, TimestampMixin):
    """Observed lead time distribution per supplier-product."""
    __tablename__ = "lead_time_profiles"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=True)

    mean_days: Mapped[float] = mapped_column(Numeric(6, 2), default=7.0)
    std_days: Mapped[float] = mapped_column(Numeric(6, 2), default=1.0)
    min_days: Mapped[int] = mapped_column(Integer, default=3)
    max_days: Mapped[int] = mapped_column(Integer, default=14)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)


class ConsumptionHistory(Base, UUIDMixin, TimestampMixin):
    """Daily consumption aggregate per product-location — used for forecasting."""
    __tablename__ = "consumption_history"
    __table_args__ = (
        UniqueConstraint("location_id", "product_id", "consumption_date", name="uq_consumption_day"),
    )

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)

    consumption_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity_consumed: Mapped[int] = mapped_column(Integer, default=0)
    data_source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # EPR, MANUAL, MOVEMENT_DERIVED


class ExpiryBatchLot(Base, UUIDMixin, TimestampMixin):
    """Batch/lot tracking with expiry for items that require it."""
    __tablename__ = "expiry_batch_lots"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inventory_locations.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)

    batch_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
    quarantine_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
