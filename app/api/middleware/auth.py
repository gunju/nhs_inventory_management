"""
FastAPI dependency: get current user from JWT, enforce RBAC and tenant isolation.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.errors import forbidden, http_error
from app.core.security import verify_access_token
from app.db.session import get_db
from app.models.user import User, ROLE_PLATFORM_ADMIN
from fastapi import status

_bearer = HTTPBearer(auto_error=False)


def _get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    if not credentials:
        raise http_error(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Missing bearer token")
    try:
        return verify_access_token(credentials.credentials)
    except JWTError as exc:
        raise http_error(status.HTTP_401_UNAUTHORIZED, "TOKEN_INVALID", str(exc))


def get_current_user(
    payload: Annotated[dict, Depends(_get_token_payload)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user_id = payload.get("sub")
    if not user_id:
        raise http_error(status.HTTP_401_UNAUTHORIZED, "TOKEN_INVALID", "No subject in token")

    user = db.get(User, uuid.UUID(user_id))
    if not user or not user.is_active or user.is_deleted:
        raise http_error(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*role_names: str):
    """Factory: returns a dependency that enforces at least one of the given roles."""
    def _check(user: CurrentUser) -> User:
        if user.is_superuser:
            return user
        if ROLE_PLATFORM_ADMIN in user.get_roles():
            return user
        if not user.get_roles().intersection(set(role_names)):
            raise forbidden(f"Required role(s): {', '.join(role_names)}")
        return user
    return Depends(_check)


def require_trust_access(trust_id: uuid.UUID, user: User) -> None:
    """Enforce that a user may only access data for their own trust, unless platform_admin."""
    if user.is_superuser or ROLE_PLATFORM_ADMIN in user.get_roles():
        return
    if user.trust_id != trust_id:
        raise forbidden("Cross-tenant access denied")
