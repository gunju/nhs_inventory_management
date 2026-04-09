from app.schemas.copilot import InventoryRecommendationRequest
from app.services.copilot_service import CopilotService


def test_retrieval_returns_protocol_evidence(db_session):
    from app.rag.retriever import ProtocolRetriever

    retriever = ProtocolRetriever()
    results = retriever.retrieve("oxygen saturation declines despite home monitoring", pathway="virtual_ward_respiratory")
    assert isinstance(results, list)
    assert results


def test_citation_presence_and_vertical_slice(db_session):
    service = CopilotService(db_session)
    response = service.run_inventory_copilot(
        InventoryRecommendationRequest(
            patient_pseudo_id="P001",
            case_summary="Patient on virtual ward with COPD exacerbation and declining oxygen saturation over 48 hours.",
        )
    )

    assert response.recommended_bundles
    assert response.recommended_bundles[0].rationale.citations


def test_insufficient_evidence_behaviour(db_session):
    service = CopilotService(db_session)
    response = service.run_inventory_copilot(
        InventoryRecommendationRequest(
            patient_pseudo_id="P003",
            case_summary="Orthopaedic rehab equipment request unrelated to virtual ward respiratory protocols.",
        )
    )

    assert response.warnings
