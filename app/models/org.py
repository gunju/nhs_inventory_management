"""
Organisational hierarchy: Trust → Hospital → Department → Ward
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin, UUIDMixin, SoftDeleteMixin


class Trust(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """NHS Trust — top-level tenant."""
    __tablename__ = "trusts"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ods_code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    hospitals: Mapped[list["Hospital"]] = relationship(back_populates="trust")


class Hospital(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "hospitals"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ods_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    trust: Mapped["Trust"] = relationship(back_populates="hospitals")
    departments: Mapped[list["Department"]] = relationship(back_populates="hospital")


class Department(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "departments"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    hospital_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("hospitals.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. WARD, THEATRE, STORE
    cost_centre: Mapped[str | None] = mapped_column(String(50), nullable=True)

    hospital: Mapped["Hospital"] = relationship(back_populates="departments")
    wards: Mapped[list["Ward"]] = relationship(back_populates="department")


class Ward(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "wards"

    trust_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=False, index=True)
    hospital_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("hospitals.id"), nullable=False, index=True)
    department_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("departments.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ward_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # ICU, GENERAL, THEATRE, STORE
    bed_count: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    department: Mapped["Department"] = relationship(back_populates="wards")
