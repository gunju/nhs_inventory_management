"""Auth endpoints: login, refresh, me."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from jose import JWTError
from sqlalchemy.orm import Session

from app.api.middleware.auth import CurrentUser
from app.core.errors import http_error
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.repositories.user_repo import UserRepo
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserOut
from fastapi import status

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="Obtain JWT tokens")
def login(
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    repo = UserRepo(db)
    user = repo.authenticate(body.email, body.password)
    if not user:
        raise http_error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Email or password incorrect")
    user.last_login_at = datetime.now(tz=timezone.utc)
    db.commit()
    roles = list(user.get_roles())
    extra = {"trust_id": str(user.trust_id) if user.trust_id else None, "roles": roles}
    return TokenResponse(
        access_token=create_access_token(str(user.id), extra),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
def refresh(body: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise JWTError("Not a refresh token")
    except JWTError as exc:
        raise http_error(status.HTTP_401_UNAUTHORIZED, "TOKEN_INVALID", str(exc))

    repo = UserRepo(db)
    import uuid
    user = repo.get_by_id(uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise http_error(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "User inactive")
    roles = list(user.get_roles())
    extra = {"trust_id": str(user.trust_id) if user.trust_id else None, "roles": roles}
    return TokenResponse(
        access_token=create_access_token(str(user.id), extra),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut, summary="Current user info")
def me(current_user: CurrentUser) -> UserOut:
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        trust_id=str(current_user.trust_id) if current_user.trust_id else None,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        roles=list(current_user.get_roles()),
    )
