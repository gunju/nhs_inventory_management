from datetime import datetime

from pydantic import BaseModel, Field


class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    quote: str
    url_or_path: str


class ExplainabilityNote(BaseModel):
    label: str
    detail: str
    source: str


class Rationale(BaseModel):
    summary: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float
    insufficient_evidence: bool
    explainability_notes: list[ExplainabilityNote] = Field(default_factory=list)


class InventoryItemRecommendation(BaseModel):
    sku_id: str
    item_name: str
    qty: int
    unit: str
    substitutions: list[str] = Field(default_factory=list)
    rationale: str
    decision_factors: list[str] = Field(default_factory=list)


class RecommendationExplainability(BaseModel):
    patient_signals: list[str] = Field(default_factory=list)
    rules_applied: list[str] = Field(default_factory=list)
    governance_notes: list[str] = Field(default_factory=list)


class RecommendedBundle(BaseModel):
    bundle_name: str
    items: list[InventoryItemRecommendation]
    rationale: Rationale
    explainability: RecommendationExplainability


class WarningMessage(BaseModel):
    type: str
    detail: str


class AuditMetadata(BaseModel):
    model_version: str
    retriever_version: str
    timestamp: datetime


class PatientRequirement(BaseModel):
    pathway_id: str
    likely_monitoring_needs: list[str]
    urgency_level: str
    specialist_review_likelihood: str
    recommended_care_context: str


class InventoryRecommendationRequest(BaseModel):
    patient_pseudo_id: str
    case_summary: str
    site_id: str = "site_01"
    user_role: str = "clinical_ops_coordinator"


class InventoryRecommendationResponse(BaseModel):
    request_id: str
    patient_pseudo_id: str
    pathway_id: str
    patient_requirements: PatientRequirement
    recommended_bundles: list[RecommendedBundle]
    warnings: list[WarningMessage]
    audit: AuditMetadata
