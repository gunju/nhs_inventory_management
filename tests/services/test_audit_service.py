from app.services.audit_service import AuditService


def test_audit_log_creation(db_session):
    service = AuditService(db_session)
    log = service.create_log(
        request_id="req_test",
        user_role="clinical_ops_coordinator",
        model_version="v1",
        retriever_version="r1",
        retrieved_chunk_ids=["chunk_1"],
        final_output={"status": "ok"},
    )

    assert log.request_id == "req_test"
    assert "chunk_1" in log.retrieved_chunk_ids
