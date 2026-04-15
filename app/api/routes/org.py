"""Organisation, product, and master data endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.middleware.auth import CurrentUser
from app.db.session import get_db
from app.models.inventory import InventoryLocation
from app.models.org import Department, Hospital, Trust, Ward
from app.models.product import Product

router = APIRouter()


@router.get("/trusts", summary="List trusts accessible to user")
def list_trusts(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    if current_user.is_superuser:
        rows = db.scalars(select(Trust).where(Trust.deleted_at.is_(None))).all()
    else:
        rows = db.scalars(
            select(Trust).where(Trust.id == current_user.trust_id, Trust.deleted_at.is_(None))
        ).all()
    return [{"id": str(t.id), "name": t.name, "ods_code": t.ods_code} for t in rows]


@router.get("/hospitals", summary="Hospitals for user's trust")
def list_hospitals(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    stmt = select(Hospital).where(
        Hospital.trust_id == current_user.trust_id, Hospital.deleted_at.is_(None)
    )
    rows = db.scalars(stmt).all()
    return [{"id": str(h.id), "name": h.name, "ods_code": h.ods_code} for h in rows]


@router.get("/locations", summary="Inventory locations for user's trust")
def list_locations(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    stmt = select(InventoryLocation).where(
        InventoryLocation.trust_id == current_user.trust_id,
        InventoryLocation.deleted_at.is_(None),
    )
    rows = db.scalars(stmt).all()
    return [
        {"id": str(l.id), "name": l.name, "type": l.location_type,
         "ward_id": str(l.ward_id) if l.ward_id else None}
        for l in rows
    ]


@router.get("/products", summary="Product catalogue for user's trust")
def list_products(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    search: str | None = None,
    is_critical: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = select(Product).where(Product.deleted_at.is_(None)).limit(limit).offset(offset)
    if current_user.trust_id:
        stmt = stmt.where((Product.trust_id == current_user.trust_id) | (Product.trust_id.is_(None)))
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%"))
    if is_critical is not None:
        stmt = stmt.where(Product.is_critical == is_critical)
    rows = db.scalars(stmt).all()
    return [
        {"id": str(p.id), "name": p.name, "sku": p.sku,
         "is_critical": p.is_critical, "gtin": p.gtin}
        for p in rows
    ]
