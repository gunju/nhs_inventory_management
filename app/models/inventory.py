import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventoryCatalog(Base):
    __tablename__ = "inventory_catalog"

    sku_id: Mapped[str] = mapped_column(String, primary_key=True)
    item_name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(50), default="each")
    pathway: Mapped[str] = mapped_column(String(100))
    substitution_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)
    default_bundle: Mapped[str | None] = mapped_column(String(100), nullable=True)


class InventoryLevel(Base):
    __tablename__ = "inventory_levels"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"lvl_{uuid.uuid4().hex[:12]}")
    site_id: Mapped[str] = mapped_column(String(50), index=True)
    sku_id: Mapped[str] = mapped_column(ForeignKey("inventory_catalog.sku_id"), index=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InventoryConsumptionHistory(Base):
    __tablename__ = "inventory_consumption_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"hist_{uuid.uuid4().hex[:12]}")
    site_id: Mapped[str] = mapped_column(String(50), index=True)
    sku_id: Mapped[str] = mapped_column(ForeignKey("inventory_catalog.sku_id"), index=True)
    usage_date: Mapped[date] = mapped_column(Date, index=True)
    quantity_used: Mapped[int] = mapped_column(Integer)
    pathway: Mapped[str] = mapped_column(String(100))


class PathwayEvent(Base):
    __tablename__ = "pathway_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    patient_pseudo_id: Mapped[str] = mapped_column(String(50), index=True)
    pathway_id: Mapped[str] = mapped_column(String(100), index=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    severity_score: Mapped[float] = mapped_column(Float, default=0.0)
