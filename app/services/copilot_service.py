from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.recommendation import RecommendationRun
from app.rag.retriever import ProtocolRetriever
from app.schemas.copilot import InventoryRecommendationRequest, InventoryRecommendationResponse
from app.services.audit_service import AuditService
from app.services.inventory_service import InventoryRecommendationEngine
from app.services.patient_requirement_service import PatientRequirementService
from app.utils.json import dumps


class CopilotService:
    def __init__(self, db: Session):
        self.db = db
        self.requirements = PatientRequirementService()
        self.retriever = ProtocolRetriever()
        self.inventory = InventoryRecommendationEngine(db)
        self.audit = AuditService(db)

    def run_inventory_copilot(self, payload: InventoryRecommendationRequest) -> InventoryRecommendationResponse:
        patient_requirements = self.requirements.extract(payload.case_summary)
        evidence = self.retriever.retrieve(payload.case_summary, pathway=patient_requirements.pathway_id)
        bundles, warnings, confidence, insufficient_evidence = self.inventory.recommend(
            patient_requirements=patient_requirements,
            evidence=evidence,
            site_id=payload.site_id,
            case_summary=payload.case_summary,
        )

        response = InventoryRecommendationResponse(
            request_id="req_" + datetime.utcnow().strftime("%Y%m%d%H%M%S%f"),
            patient_pseudo_id=payload.patient_pseudo_id,
            pathway_id=patient_requirements.pathway_id,
            patient_requirements=patient_requirements,
            recommended_bundles=bundles,
            warnings=warnings,
            audit={
                "model_version": "lora-extraction-v1",
                "retriever_version": self.retriever.version,
                "timestamp": datetime.utcnow(),
            },
        )
        run = RecommendationRun(
            patient_pseudo_id=payload.patient_pseudo_id,
            pathway_id=patient_requirements.pathway_id,
            request_payload=dumps(payload.model_dump()),
            response_payload=dumps(response.model_dump()),
            confidence=confidence,
            insufficient_evidence=insufficient_evidence,
        )
        self.db.add(run)
        self.db.commit()

        self.audit.create_log(
            request_id=response.request_id,
            user_role=payload.user_role,
            model_version=response.audit.model_version,
            retriever_version=response.audit.retriever_version,
            retrieved_chunk_ids=[item.chunk_id for item in evidence],
            final_output=response.model_dump(),
        )
        return response
