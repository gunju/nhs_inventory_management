import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PatientCase(Base):
    __tablename__ = "patient_cases"

    patient_pseudo_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    case_summary: Mapped[str] = mapped_column(Text)
    pathway_hint: Mapped[str] = mapped_column(String(100))
    acuity_hint: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReferralNote(Base):
    __tablename__ = "referral_notes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"ref_{uuid.uuid4().hex[:12]}")
    patient_pseudo_id: Mapped[str] = mapped_column(String(50), index=True)
    specialty_requested: Mapped[str] = mapped_column(String(100))
    note_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
