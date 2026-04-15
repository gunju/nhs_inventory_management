"""User + role repository — all DB queries for auth/RBAC."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password, verify_password
from app.models.user import Role, User, UserRoleAssignment


class UserRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(User)
            .where(User.email == email, User.deleted_at.is_(None))
            .options(selectinload(User.role_assignments).selectinload(UserRoleAssignment.role))
        )
        return self.db.scalar(stmt)

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .options(selectinload(User.role_assignments).selectinload(UserRoleAssignment.role))
        )
        return self.db.scalar(stmt)

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    def create(self, email: str, password: str, full_name: str | None = None,
               trust_id: uuid.UUID | None = None, is_superuser: bool = False) -> User:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            trust_id=trust_id,
            is_superuser=is_superuser,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def assign_role(self, user_id: uuid.UUID, role_name: str,
                    trust_id: uuid.UUID | None = None) -> UserRoleAssignment:
        role = self.db.scalar(select(Role).where(Role.name == role_name))
        if not role:
            role = Role(name=role_name)
            self.db.add(role)
            self.db.flush()
        assignment = UserRoleAssignment(user_id=user_id, role_id=role.id, trust_id=trust_id)
        self.db.add(assignment)
        self.db.flush()
        return assignment

    def ensure_role_exists(self, role_name: str) -> Role:
        role = self.db.scalar(select(Role).where(Role.name == role_name))
        if not role:
            role = Role(name=role_name)
            self.db.add(role)
            self.db.flush()
        return role
