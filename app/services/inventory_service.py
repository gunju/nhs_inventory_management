from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.inventory import InventoryCatalog, InventoryLevel
from app.rag.retriever import RetrievedEvidence
from app.schemas.copilot import (
    Citation,
    ExplainabilityNote,
    PatientRequirement,
    Rationale,
    RecommendedBundle,
    RecommendationExplainability,
    WarningMessage,
)


@dataclass
class ItemRule:
    sku_id: str
    bundle_name: str
    trigger_need: str
    rationale_template: str
    rule_name: str


class InventoryRecommendationEngine:
    item_rules = {
        "pulse_oximetry": ItemRule(
            sku_id="OX001",
            bundle_name="Respiratory Monitoring Kit",
            trigger_need="pulse_oximetry",
            rationale_template="Included because pulse oximetry monitoring is indicated for the identified pathway and current case signals.",
            rule_name="RR-01 Pulse oximetry for respiratory virtual ward pathway",
        ),
        "blood_pressure": ItemRule(
            sku_id="BP002",
            bundle_name="Virtual Ward Monitoring Kit",
            trigger_need="blood_pressure",
            rationale_template="Included because blood pressure monitoring supports escalation checks and home observation completeness.",
            rule_name="RR-02 Blood pressure cuff when escalation or cardiovascular observation is required",
        ),
        "temperature_monitoring": ItemRule(
            sku_id="TH003",
            bundle_name="Virtual Ward Monitoring Kit",
            trigger_need="temperature_monitoring",
            rationale_template="Included because infection or acute deterioration cues increase the need for temperature monitoring at home.",
            rule_name="RR-03 Thermometer when infection or deterioration cues are present",
        ),
        "weight_monitoring": ItemRule(
            sku_id="WS004",
            bundle_name="Heart Failure Support Kit",
            trigger_need="weight_monitoring",
            rationale_template="Included because weight trend monitoring is relevant for fluid balance and heart failure style follow-up.",
            rule_name="RR-04 Weight scale for heart failure style home monitoring",
        ),
    }

    def __init__(self, db: Session):
        self.db = db

    def recommend(
        self,
        patient_requirements: PatientRequirement,
        evidence: list[RetrievedEvidence],
        site_id: str,
        case_summary: str,
    ) -> tuple[list[RecommendedBundle], list[WarningMessage], float, bool]:
        if not evidence:
            return [], [WarningMessage(type="INSUFFICIENT_EVIDENCE", detail="No approved protocol evidence found.")], 0.0, True

        selected_rules = self._select_rules(patient_requirements, case_summary)
        selected_skus = [rule.sku_id for rule in selected_rules]
        if not selected_skus:
            return [], [WarningMessage(type="INSUFFICIENT_EVIDENCE", detail="No inventory rules matched the approved evidence-backed patient need profile.")], 0.0, True

        catalog_rows = self.db.query(InventoryCatalog).filter(InventoryCatalog.sku_id.in_(selected_skus)).all()
        catalog_by_sku = {row.sku_id: row for row in catalog_rows}
        levels = {
            row.sku_id: row
            for row in self.db.query(InventoryLevel)
            .filter(InventoryLevel.site_id == site_id, InventoryLevel.sku_id.in_(selected_skus))
            .all()
        }
        substitutions = self._build_substitutions()
        warnings = self._build_stock_warnings(catalog_rows, levels, site_id)
        citations = self._build_citations(evidence)
        confidence = round(sum(item.score for item in evidence) / len(evidence), 2)
        patient_signals = self._extract_patient_signals(patient_requirements, case_summary)

        bundle_name = self._derive_bundle_name(selected_rules, patient_requirements.pathway_id)
        items = []
        rules_applied: list[str] = []
        for rule in selected_rules:
            row = catalog_by_sku.get(rule.sku_id)
            if row is None:
                warnings.append(
                    WarningMessage(
                        type="CATALOG_GAP",
                        detail=f"Configured item {rule.sku_id} is not available in the current catalog for {site_id}.",
                    )
                )
                continue
            decision_factors = [
                f"Monitoring need: {rule.trigger_need}",
                f"Urgency: {patient_requirements.urgency_level}",
                f"Care context: {patient_requirements.recommended_care_context}",
            ]
            if patient_requirements.specialist_review_likelihood in {"high", "moderate"}:
                decision_factors.append(
                    f"Specialist review likelihood: {patient_requirements.specialist_review_likelihood}"
                )
            items.append(
                {
                    "sku_id": row.sku_id,
                    "item_name": row.item_name,
                    "qty": 1 if patient_requirements.urgency_level == "routine" else 2 if row.sku_id == "TH003" else 1,
                    "unit": row.unit,
                    "substitutions": [
                        candidate
                        for candidate in substitutions[row.substitution_group]
                        if candidate != row.sku_id
                    ]
                    if row.substitution_group
                    else [],
                    "rationale": rule.rationale_template,
                    "decision_factors": decision_factors,
                }
            )
            rules_applied.append(rule.rule_name)

        rationale = Rationale(
            summary=self._build_summary(patient_requirements, patient_signals),
            citations=citations,
            confidence=confidence,
            insufficient_evidence=False,
            explainability_notes=[
                ExplainabilityNote(
                    label="Patient signals interpreted",
                    detail=", ".join(patient_signals),
                    source="structured_patient_requirements",
                ),
                ExplainabilityNote(
                    label="Rule set applied",
                    detail="; ".join(rules_applied),
                    source="deterministic_inventory_rules",
                ),
                ExplainabilityNote(
                    label="Evidence policy",
                    detail="Recommendations are returned only when approved protocol evidence is present.",
                    source="rag_governance_policy",
                ),
            ],
        )
        explainability = RecommendationExplainability(
            patient_signals=patient_signals,
            rules_applied=rules_applied,
            governance_notes=[
                "Decision support only. Clinician review is required before action.",
                "Inventory logic is rule-based and constrained by approved protocol evidence.",
                "Confidence reflects retrieval strength, not autonomous clinical certainty.",
            ],
        )
        return [
            RecommendedBundle(
                bundle_name=bundle_name,
                items=items,
                rationale=rationale,
                explainability=explainability,
            )
        ], warnings, confidence, False

    def _select_rules(self, patient_requirements: PatientRequirement, case_summary: str) -> list[ItemRule]:
        selected = [
            self.item_rules[need]
            for need in patient_requirements.likely_monitoring_needs
            if need in self.item_rules
        ]
        lowered = case_summary.lower()
        if patient_requirements.pathway_id == "virtual_ward_respiratory" and "pulse_oximetry" not in patient_requirements.likely_monitoring_needs:
            selected.append(self.item_rules["pulse_oximetry"])
        if any(token in lowered for token in ["infection", "fever", "acute deterioration"]) and self.item_rules["temperature_monitoring"] not in selected:
            selected.append(self.item_rules["temperature_monitoring"])
        if patient_requirements.urgency_level == "urgent" and all(rule.sku_id != "BP002" for rule in selected):
            selected.append(self.item_rules["blood_pressure"])
        unique_by_sku: dict[str, ItemRule] = {rule.sku_id: rule for rule in selected}
        return list(unique_by_sku.values())

    def _derive_bundle_name(self, rules: list[ItemRule], pathway_id: str) -> str:
        bundle_names = {rule.bundle_name for rule in rules}
        if "Heart Failure Support Kit" in bundle_names:
            return "Mixed Virtual Ward Support Kit"
        if pathway_id == "virtual_ward_respiratory":
            return "Respiratory Monitoring Kit"
        return next(iter(bundle_names), "Virtual Ward Starter Kit")

    def _build_stock_warnings(
        self,
        catalog_rows: list[InventoryCatalog],
        levels: dict[str, InventoryLevel],
        site_id: str,
    ) -> list[WarningMessage]:
        warnings: list[WarningMessage] = []
        for row in catalog_rows:
            level = levels.get(row.sku_id)
            on_hand = level.quantity_on_hand if level else 0
            if on_hand <= row.reorder_point:
                warnings.append(
                    WarningMessage(
                        type="STOCKOUT_RISK",
                        detail=f"{row.item_name} at or below reorder point for {site_id}.",
                    )
                )
        return warnings

    def _build_citations(self, evidence: list[RetrievedEvidence]) -> list[Citation]:
        return [
            Citation(
                doc_id=item.doc_id,
                chunk_id=item.chunk_id,
                quote=item.content[:180],
                url_or_path=item.source_path,
            )
            for item in evidence[:3]
        ]

    def _build_summary(self, patient_requirements: PatientRequirement, patient_signals: list[str]) -> str:
        signals = ", ".join(patient_signals[:3]) if patient_signals else "approved pathway evidence"
        return (
            "Recommended because approved protocol evidence aligns with the identified care pathway "
            f"and the following interpreted patient signals: {signals}."
        )

    def _extract_patient_signals(self, patient_requirements: PatientRequirement, case_summary: str) -> list[str]:
        signals = [
            f"pathway={patient_requirements.pathway_id}",
            f"urgency={patient_requirements.urgency_level}",
        ]
        signals.extend(
            [f"monitoring={need}" for need in patient_requirements.likely_monitoring_needs]
        )
        lowered = case_summary.lower()
        if "declining" in lowered or "worsening" in lowered:
            signals.append("deterioration_trend")
        if "infection" in lowered or "fever" in lowered:
            signals.append("infection_cue")
        if "heart failure" in lowered:
            signals.append("heart_failure_context")
        return signals

    def _build_substitutions(self) -> dict[str, list[str]]:
        rows = self.db.query(InventoryCatalog).all()
        grouped: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            if row.substitution_group:
                grouped[row.substitution_group].append(row.sku_id)
        return grouped
