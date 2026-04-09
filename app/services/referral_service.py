from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.finetuning.inference_adapter import LoraInferenceAdapter
from app.models.patient import PatientCase, ReferralNote
from app.rag.retriever import ProtocolRetriever
from app.schemas.copilot import Citation
from app.schemas.referral import ReferralDraftResponse


class ReferralService:
    def __init__(self, db: Session):
        self.db = db
        self.retriever = ProtocolRetriever()
        settings = get_settings()
        self.adapter = LoraInferenceAdapter(settings.base_llm_model, settings.triage_adapter_path)

    def build_draft(self, patient_pseudo_id: str, specialty_requested: str) -> ReferralDraftResponse:
        patient_case = self.db.get(PatientCase, patient_pseudo_id)
        note = (
            self.db.query(ReferralNote)
            .filter(ReferralNote.patient_pseudo_id == patient_pseudo_id)
            .order_by(ReferralNote.created_at.desc())
            .first()
        )
        case_text = note.note_text if note else (patient_case.case_summary if patient_case else "")
        evidence = self.retriever.retrieve(case_text, pathway="virtual_ward_respiratory")

        route = {"type": "A_AND_G", "reasoning": "Advice and guidance suggested before routine referral due to protocol cues."}
        if self.adapter.available():
            prompt = (
                "Classify referral route in JSON with fields type and reasoning.\n"
                f"Specialty: {specialty_requested}\nCase: {case_text}"
            )
            route = self.adapter.generate_json(prompt)

        facts = [
            {"label": "Current pathway", "value": patient_case.pathway_hint if patient_case else "unknown"},
            {"label": "Clinical signal", "value": "Worsening respiratory observations" if "oxygen" in case_text.lower() else "Monitor and review"},
        ]
        citations = [
            Citation(
                doc_id=item.doc_id,
                chunk_id=item.chunk_id,
                quote=item.content[:180],
                url_or_path=item.source_path,
            )
            for item in evidence[:2]
        ]
        return ReferralDraftResponse(
            referral_draft_id=str(uuid.uuid4()),
            patient_pseudo_id=patient_pseudo_id,
            specialty_requested=specialty_requested,
            summary=case_text[:180],
            key_clinical_facts=facts,
            suggested_route=route,
            protocol_context={"citations": citations},
            required_human_approval=True,
        )
