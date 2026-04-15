"""Integration run management endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.middleware.auth import CurrentUser, require_roles
from app.db.session import get_db
from app.integrations.registry import get_adapter
from app.models.user import ROLE_SUPPLY_CHAIN_MANAGER, ROLE_TRUST_ADMIN

router = APIRouter()

_ROLES = (ROLE_SUPPLY_CHAIN_MANAGER, ROLE_TRUST_ADMIN)


@router.post("/run/{adapter_name}", summary="Trigger an integration adapter run")
def run_adapter(
    adapter_name: str,
    current_user: CurrentUser,
    _: Annotated[None, require_roles(*_ROLES)],
    db: Annotated[Session, Depends(get_db)],
    source_ref: str | None = None,
) -> dict:
    try:
        adapter_cls = get_adapter(adapter_name)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"code": "ADAPTER_NOT_FOUND", "message": str(exc)})

    adapter = adapter_cls(db, current_user.trust_id)
    run = adapter.run(source_ref=source_ref)
    return {
        "run_id": str(run.id),
        "adapter": adapter_name,
        "status": run.status,
        "records_ingested": run.records_ingested,
        "records_failed": run.records_failed,
        "error_message": run.error_message,
    }
