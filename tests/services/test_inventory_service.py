from app.schemas.copilot import PatientRequirement
from app.services.inventory_service import InventoryRecommendationEngine


def test_inventory_mapping_returns_bundle_with_citations(db_session):
    engine = InventoryRecommendationEngine(db_session)
    evidence = [
        type("Evidence", (), {"doc_id": "doc_1", "chunk_id": "chunk_1", "content": "Pulse oximetry monitoring required.", "source_path": "/docs/protocol.md", "score": 0.9})
    ]
    patient_requirements = PatientRequirement(
        pathway_id="virtual_ward_respiratory",
        likely_monitoring_needs=["pulse_oximetry", "blood_pressure", "temperature_monitoring"],
        urgency_level="urgent",
        specialist_review_likelihood="high",
        recommended_care_context="virtual ward support",
    )
    bundles, warnings, confidence, insufficient = engine.recommend(
        patient_requirements=patient_requirements,
        evidence=evidence,
        site_id="site_01",
        case_summary="Patient on virtual ward with declining oxygen saturation and infection concern.",
    )

    assert bundles
    assert bundles[0].items
    assert any(item.sku_id == "OX001" for item in bundles[0].items)
    assert any(item.sku_id == "TH003" for item in bundles[0].items)
    assert bundles[0].rationale.citations
    assert bundles[0].rationale.explainability_notes
    assert bundles[0].explainability.rules_applied
    assert confidence > 0
    assert insufficient is False
    assert any(warning.type == "STOCKOUT_RISK" for warning in warnings)


def test_inventory_variation_by_monitoring_need(db_session):
    engine = InventoryRecommendationEngine(db_session)
    evidence = [
        type("Evidence", (), {"doc_id": "doc_1", "chunk_id": "chunk_1", "content": "Pulse oximetry monitoring required.", "source_path": "/docs/protocol.md", "score": 0.9})
    ]
    stable_requirements = PatientRequirement(
        pathway_id="virtual_ward_respiratory",
        likely_monitoring_needs=["pulse_oximetry"],
        urgency_level="routine",
        specialist_review_likelihood="moderate",
        recommended_care_context="virtual ward support",
    )
    urgent_requirements = PatientRequirement(
        pathway_id="virtual_ward_respiratory",
        likely_monitoring_needs=["pulse_oximetry", "blood_pressure", "temperature_monitoring"],
        urgency_level="urgent",
        specialist_review_likelihood="high",
        recommended_care_context="virtual ward support",
    )

    stable_bundles, _, _, _ = engine.recommend(stable_requirements, evidence, "site_01", "Stable respiratory follow-up.")
    urgent_bundles, _, _, _ = engine.recommend(
        urgent_requirements,
        evidence,
        "site_01",
        "Worsening respiratory case with infection and declining oxygen saturation.",
    )

    stable_skus = {item.sku_id for item in stable_bundles[0].items}
    urgent_skus = {item.sku_id for item in urgent_bundles[0].items}
    assert stable_skus != urgent_skus
    assert stable_skus == {"OX001"}
    assert {"OX001", "BP002", "TH003"} <= urgent_skus
