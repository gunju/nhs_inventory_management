from pydantic import BaseModel, Field

from app.schemas.copilot import Citation


class KeyClinicalFact(BaseModel):
    label: str
    value: str


class SuggestedRoute(BaseModel):
    type: str
    reasoning: str


class ReferralProtocolContext(BaseModel):
    citations: list[Citation] = Field(default_factory=list)


class ReferralDraftResponse(BaseModel):
    referral_draft_id: str
    patient_pseudo_id: str
    specialty_requested: str
    summary: str
    key_clinical_facts: list[KeyClinicalFact]
    suggested_route: SuggestedRoute
    protocol_context: ReferralProtocolContext
    required_human_approval: bool = True
