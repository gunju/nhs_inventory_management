from __future__ import annotations

from app.core.config import get_settings
from app.finetuning.inference_adapter import LoraInferenceAdapter
from app.schemas.copilot import PatientRequirement


class PatientRequirementService:
    def __init__(self) -> None:
        settings = get_settings()
        self.adapter = LoraInferenceAdapter(settings.base_llm_model, settings.extraction_adapter_path)

    def extract(self, case_summary: str) -> PatientRequirement:
        if self.adapter.available():
            prompt = (
                "Extract a structured NHS-style patient requirement object in JSON only.\n"
                f"Case note: {case_summary}"
            )
            raw = self.adapter.generate_json(prompt)
            return PatientRequirement.model_validate(raw)

        lowered = case_summary.lower()
        pathway_id = "virtual_ward_respiratory" if any(
            token in lowered for token in ["spo2", "oxygen", "respiratory", "breathless", "copd"]
        ) else "virtual_ward_general"
        monitoring: list[str] = []
        if pathway_id == "virtual_ward_respiratory":
            monitoring.append("pulse_oximetry")
        if any(token in lowered for token in ["declining", "worsening", "exacerbation", "blood pressure", "hypertension"]):
            monitoring.append("blood_pressure")
        if any(token in lowered for token in ["fever", "infection", "temperature", "sepsis", "acute deterioration"]):
            monitoring.append("temperature_monitoring")
        if "heart failure" in lowered:
            monitoring.append("weight_monitoring")
            monitoring.append("blood_pressure")
        if not monitoring:
            monitoring.append("blood_pressure")
        urgency = "urgent" if any(token in lowered for token in ["declining", "worsening", "urgent"]) else "routine"
        specialist = "high" if "declining" in lowered else "moderate"
        care_context = "virtual ward support"
        return PatientRequirement(
            pathway_id=pathway_id,
            likely_monitoring_needs=list(dict.fromkeys(monitoring)),
            urgency_level=urgency,
            specialist_review_likelihood=specialist,
            recommended_care_context=care_context,
        )
