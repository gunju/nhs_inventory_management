from app.services.referral_service import ReferralService


def test_referral_draft_schema(db_session):
    service = ReferralService(db_session)
    draft = service.build_draft("P001", "respiratory")

    assert draft.patient_pseudo_id == "P001"
    assert draft.required_human_approval is True
    assert draft.suggested_route.type in {"A_AND_G", "REFERRAL_ASSESSMENT", "ROUTINE_REFERRAL"}
