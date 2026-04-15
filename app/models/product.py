"""
Product master data: suppliers, products, catalog, barcodes.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin, UUIDMixin, SoftDeleteMixin


class ProductCategory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "product_categories"

    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("product_categories.id"), nullable=True)
    criticality: Mapped[str] = mapped_column(String(20), default="standard")  # critical / standard / low

    children: Mapped[list["ProductCategory"]] = relationship("ProductCategory")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class UOM(Base, UUIDMixin, TimestampMixin):
    """Unit of Measure master."""
    __tablename__ = "uoms"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_conversion: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)


class Supplier(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "suppliers"

    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    catalog_items: Mapped[list["CatalogItem"]] = relationship(back_populates="supplier")


class Product(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"

    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("product_categories.id"), nullable=True, index=True)
    uom_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("uoms.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    gtin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    udi: Mapped[str | None] = mapped_column(String(100), nullable=True)  # unique device identifier placeholder
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    therapeutic_area: Mapped[str | None] = mapped_column(String(200), nullable=True)

    category: Mapped["ProductCategory | None"] = relationship(back_populates="products")
    aliases: Mapped[list["ProductAlias"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    barcodes: Mapped[list["BarcodeIdentifier"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    catalog_items: Mapped[list["CatalogItem"]] = relationship(back_populates="product")


class ProductAlias(Base, UUIDMixin, TimestampMixin):
    """Maps alternative names / supplier codes to canonical product."""
    __tablename__ = "product_aliases"
    __table_args__ = (UniqueConstraint("product_id", "alias", name="uq_product_alias"),)

    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    alias_type: Mapped[str] = mapped_column(String(50), default="supplier_code")  # supplier_code, trade_name, legacy_sku
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="aliases")


class BarcodeIdentifier(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "barcode_identifiers"

    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    barcode_type: Mapped[str] = mapped_column(String(20), nullable=False)  # EAN13, GS1, QR
    barcode_value: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    product: Mapped["Product"] = relationship(back_populates="barcodes")


class CatalogItem(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Supplier-specific pricing/packaging for a product."""
    __tablename__ = "catalog_items"

    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False, index=True)
    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)

    supplier_sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pack_size: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    contract_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="catalog_items")
    supplier: Mapped["Supplier"] = relationship(back_populates="catalog_items")
