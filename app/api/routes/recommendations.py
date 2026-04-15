"""Recommendation endpoints with human-in-the-loop approval workflow."""
from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.middleware.auth import CurrentUser, require_roles
from app.core.errors import not_found
from app.db.session import get_db
from app.models.ai import (
    RecommendationDecision, ReorderRecommendation, RedistributionRecommendation,
)
from app.models.product import Product
from app.models.inventory import InventoryLocation
from app.models.user import ROLE_AI_REVIEWER, ROLE_SUPPLY_CHAIN_MANAGER, ROLE_WARD_MANAGER
from app.recommendations.engine import RecommendationEngine
from app.schemas.recommendations import (
    DecisionRequest, EvidenceRef, ReorderRecommendationOut, RedistributionRecommendationOut,
    RecommendationRunRequest,
)

router = APIRouter()

_REVIEW_ROLES = (ROLE_AI_REVIEWER, ROLE_SUPPLY_CHAIN_MANAGER)
_READ_ROLES = (ROLE_AI_REVIEWER, ROLE_SUPPLY_CHAIN_MANAGER, ROLE_WARD_MANAGER)


def _parse_evidence(evidence_json: str | None) -> list[EvidenceRef]:
    if not evidence_json:
        return []
    try:
        return [EvidenceRef(**e) for e in json.loads(evidence_json)]
    except Exception:
        return []


@router.post("/run", summary="Generate recommendations from latest forecast")
def run_recommendations(
    body: RecommendationRunRequest,
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_REVIEW_ROLES)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    engine = RecommendationEngine(db)
    reorder_n, redist_n = engine.run(current_user.trust_id, body.run_id)
    return {"reorder_recommendations": reorder_n, "redistribution_recommendations": redist_n}


@router.get("/reorder", response_model=list[ReorderRecommendationOut])
def list_reorder(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_READ_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(default=None),
    urgency: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ReorderRecommendationOut]:
    stmt = (
        select(ReorderRecommendation, Product, InventoryLocation)
        .join(Product, ReorderRecommendation.product_id == Product.id)
        .join(InventoryLocation, ReorderRecommendation.location_id == InventoryLocation.id)
        .where(ReorderRecommendation.trust_id == current_user.trust_id)
        .order_by(ReorderRecommendation.created_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(ReorderRecommendation.review_status == status)
    if urgency:
        stmt = stmt.where(ReorderRecommendation.urgency == urgency)
    rows = db.execute(stmt).all()
    return [
        ReorderRecommendationOut(
            id=r.id, product_id=r.product_id, product_name=p.name,
            location_id=r.location_id, location_name=loc.name,
            suggested_quantity=r.suggested_quantity, urgency=r.urgency,
            confidence=r.confidence, rationale=r.rationale,
            evidence=_parse_evidence(r.evidence_json),
            review_status=r.review_status,
            created_at=r.created_at.isoformat(),
        )
        for r, p, loc in rows
    ]


@router.get("/redistribute", response_model=list[RedistributionRecommendationOut])
def list_redistribution(
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_READ_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[RedistributionRecommendationOut]:
    stmt = (
        select(RedistributionRecommendation, Product)
        .join(Product, RedistributionRecommendation.product_id == Product.id)
        .where(RedistributionRecommendation.trust_id == current_user.trust_id)
        .order_by(RedistributionRecommendation.created_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(RedistributionRecommendation.review_status == status)
    rows = db.execute(stmt).all()
    return [
        RedistributionRecommendationOut(
            id=r.id, product_id=r.product_id, product_name=p.name,
            source_location_id=r.source_location_id,
            target_location_id=r.target_location_id,
            suggested_quantity=r.suggested_quantity, urgency=r.urgency,
            confidence=r.confidence, rationale=r.rationale,
            evidence=_parse_evidence(r.evidence_json),
            review_status=r.review_status,
            created_at=r.created_at.isoformat(),
        )
        for r, p in rows
    ]


def _apply_decision(
    db: Session,
    trust_id: uuid.UUID,
    user_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    rec_type: str,
    body: DecisionRequest,
) -> RecommendationDecision:
    decision = RecommendationDecision(
        trust_id=trust_id,
        recommendation_id=recommendation_id,
        recommendation_type=rec_type,
        decided_by_id=user_id,
        decision=body.decision,
        rationale=body.rationale,
        snooze_until=body.snooze_until,
    )
    db.add(decision)
    db.commit()
    return decision


@router.post("/reorder/{rec_id}/approve", summary="Approve a reorder recommendation")
def approve_reorder(
    rec_id: uuid.UUID,
    body: DecisionRequest,
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_REVIEW_ROLES)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    rec = db.get(ReorderRecommendation, rec_id)
    if not rec or rec.trust_id != current_user.trust_id:
        raise not_found("ReorderRecommendation")
    rec.review_status = body.decision
    _apply_decision(db, current_user.trust_id, current_user.id, rec_id, "reorder", body)
    return {"status": body.decision, "recommendation_id": str(rec_id)}


@router.post("/reorder/{rec_id}/reject", summary="Reject a reorder recommendation")
def reject_reorder(
    rec_id: uuid.UUID,
    body: DecisionRequest,
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_REVIEW_ROLES)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    body.decision = "rejected"
    rec = db.get(ReorderRecommendation, rec_id)
    if not rec or rec.trust_id != current_user.trust_id:
        raise not_found("ReorderRecommendation")
    rec.review_status = "rejected"
    _apply_decision(db, current_user.trust_id, current_user.id, rec_id, "reorder", body)
    db.commit()
    return {"status": "rejected", "recommendation_id": str(rec_id)}


@router.post("/reorder/{rec_id}/snooze", summary="Snooze a reorder recommendation")
def snooze_reorder(
    rec_id: uuid.UUID,
    body: DecisionRequest,
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_REVIEW_ROLES)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    body.decision = "snoozed"
    rec = db.get(ReorderRecommendation, rec_id)
    if not rec or rec.trust_id != current_user.trust_id:
        raise not_found("ReorderRecommendation")
    rec.review_status = "snoozed"
    _apply_decision(db, current_user.trust_id, current_user.id, rec_id, "reorder", body)
    db.commit()
    return {"status": "snoozed", "recommendation_id": str(rec_id)}
