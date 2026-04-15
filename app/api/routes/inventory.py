"""Inventory visibility endpoints."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.middleware.auth import CurrentUser, require_roles
from app.core.pagination import PageParams, PagedResponse
from app.db.session import get_db
from app.models.user import ROLE_ANALYST, ROLE_SUPPLY_CHAIN_MANAGER, ROLE_WARD_MANAGER, ROLE_READ_ONLY
from app.repositories.inventory_repo import InventoryRepo
from app.schemas.inventory import (
    ExpiryRiskOut, MovementOut, OverstockRiskOut, StockLevelOut, StockoutRiskOut,
)

router = APIRouter()

_READ_ROLES = (ROLE_SUPPLY_CHAIN_MANAGER, ROLE_WARD_MANAGER, ROLE_ANALYST, ROLE_READ_ONLY)


@router.get("/stock-levels", response_model=list[StockLevelOut], summary="Current stock levels")
def stock_levels(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_READ_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    location_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    below_reorder_only: bool = False,
) -> list[StockLevelOut]:
    trust_id = current_user.trust_id
    if not trust_id:
        return []
    repo = InventoryRepo(db)
    rows = repo.get_stock_levels(trust_id, location_id, product_id, below_reorder_only)
    result = []
    for balance, location, product, policy in rows:
        result.append(StockLevelOut(
            location_id=location.id,
            location_name=location.name,
            product_id=product.id,
            product_name=product.name,
            sku=product.sku,
            quantity_on_hand=balance.quantity_on_hand,
            quantity_reserved=balance.quantity_reserved,
            quantity_on_order=balance.quantity_on_order,
            reorder_point=policy.reorder_point if policy else None,
            is_below_reorder=bool(policy and balance.quantity_on_hand <= policy.reorder_point),
            balance_as_of=balance.balance_as_of,
        ))
    return result


@router.get("/movements", response_model=PagedResponse[MovementOut], summary="Stock movement history")
def movements(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_READ_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    location_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PagedResponse[MovementOut]:
    trust_id = current_user.trust_id
    if not trust_id:
        return PagedResponse.build([], 0, PageParams(page=page, page_size=page_size))
    repo = InventoryRepo(db)
    params = PageParams(page=page, page_size=page_size)
    rows, total = repo.get_movements(trust_id, location_id, product_id, from_date, to_date,
                                     limit=params.page_size, offset=params.offset)
    items = [MovementOut(
        id=m.id,
        location_id=m.location_id,
        product_id=m.product_id,
        movement_type=m.movement_type,
        quantity=m.quantity,
        movement_date=m.movement_date,
        reference_id=m.reference_id,
        notes=m.notes,
    ) for m in rows]
    return PagedResponse.build(items, total, params)


@router.get("/expiring", response_model=list[ExpiryRiskOut], summary="Items expiring soon")
def expiring(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_READ_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    days_ahead: int = Query(default=30, ge=1, le=365),
) -> list[ExpiryRiskOut]:
    trust_id = current_user.trust_id
    if not trust_id:
        return []
    repo = InventoryRepo(db)
    rows = repo.get_expiry_risks(trust_id, days_ahead)
    today = date.today()
    return [
        ExpiryRiskOut(
            location_id=loc.id,
            product_id=prod.id,
            product_name=prod.name,
            sku=prod.sku,
            batch_number=lot.batch_number,
            expiry_date=lot.expiry_date,
            quantity=lot.quantity,
            days_to_expiry=(lot.expiry_date - today).days,
        )
        for lot, loc, prod in rows
    ]


@router.get("/stockouts-risk", response_model=list[StockoutRiskOut], summary="Shortage risk by horizon")
def stockouts_risk(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_READ_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    horizon_days: int = Query(default=7, ge=1, le=90),
    min_risk_score: float = Query(default=0.3, ge=0.0, le=1.0),
) -> list[StockoutRiskOut]:
    from sqlalchemy import select
    from app.models.ai import ShortageRisk
    from app.models.inventory import InventoryLocation
    from app.models.product import Product

    trust_id = current_user.trust_id
    if not trust_id:
        return []

    stmt = (
        select(ShortageRisk, InventoryLocation, Product)
        .join(InventoryLocation, ShortageRisk.location_id == InventoryLocation.id)
        .join(Product, ShortageRisk.product_id == Product.id)
        .where(
            ShortageRisk.trust_id == trust_id,
            ShortageRisk.horizon_days == horizon_days,
            ShortageRisk.risk_score >= min_risk_score,
        )
        .order_by(ShortageRisk.risk_score.desc())
    )
    rows = db.execute(stmt).all()
    return [
        StockoutRiskOut(
            location_id=loc.id,
            location_name=loc.name,
            product_id=prod.id,
            product_name=prod.name,
            sku=prod.sku,
            risk_score=risk.risk_score,
            days_to_stockout=risk.days_to_stockout,
            current_stock=risk.current_stock,
            horizon_days=horizon_days,
        )
        for risk, loc, prod in rows
    ]


@router.get("/overstock-risk", response_model=list[OverstockRiskOut], summary="Overstock risk")
def overstock_risk(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_READ_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    min_risk_score: float = Query(default=0.3, ge=0.0, le=1.0),
) -> list[OverstockRiskOut]:
    from sqlalchemy import select
    from app.models.ai import OverstockRisk
    from app.models.product import Product

    trust_id = current_user.trust_id
    if not trust_id:
        return []

    stmt = (
        select(OverstockRisk, Product)
        .join(Product, OverstockRisk.product_id == Product.id)
        .where(
            OverstockRisk.trust_id == trust_id,
            OverstockRisk.risk_score >= min_risk_score,
        )
        .order_by(OverstockRisk.risk_score.desc())
    )
    rows = db.execute(stmt).all()
    return [
        OverstockRiskOut(
            location_id=r.location_id,
            product_id=prod.id,
            product_name=prod.name,
            sku=prod.sku,
            risk_score=r.risk_score,
            excess_quantity=r.excess_quantity,
            excess_value=r.excess_value,
            days_of_cover=r.days_of_cover,
        )
        for r, prod in rows
    ]
