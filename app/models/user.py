"""
User, Role, UserRoleAssignment — multi-tenant RBAC.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin, UUIDMixin, SoftDeleteMixin

# Canonical role names
ROLE_PLATFORM_ADMIN = "platform_admin"
ROLE_TRUST_ADMIN = "trust_admin"
ROLE_SUPPLY_CHAIN_MANAGER = "supply_chain_manager"
ROLE_WARD_MANAGER = "ward_manager"
ROLE_ANALYST = "analyst"
ROLE_READ_ONLY = "read_only_user"
ROLE_AI_REVIEWER = "ai_reviewer"

ALL_ROLES = {
    ROLE_PLATFORM_ADMIN, ROLE_TRUST_ADMIN, ROLE_SUPPLY_CHAIN_MANAGER,
    ROLE_WARD_MANAGER, ROLE_ANALYST, ROLE_READ_ONLY, ROLE_AI_REVIEWER,
}


class Role(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    assignments: Mapped[list["UserRoleAssignment"]] = relationship(back_populates="role")


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(back_populates="user", foreign_keys="UserRoleAssignment.user_id", cascade="all, delete-orphan")

    def get_roles(self) -> set[str]:
        return {ra.role.name for ra in self.role_assignments if ra.role}

    def has_role(self, role_name: str) -> bool:
        return role_name in self.get_roles()


class UserRoleAssignment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_role_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "trust_id", name="uq_user_role_trust"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("roles.id"), nullable=False, index=True)
    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("hospitals.id"), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("departments.id"), nullable=True)
    granted_by_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    user: Mapped["User"] = relationship(back_populates="role_assignments", foreign_keys=[user_id])
    role: Mapped["Role"] = relationship(back_populates="assignments")
