from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.utils.json import dumps


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def create_log(
        self,
        request_id: str,
        user_role: str,
        model_version: str,
        retriever_version: str,
        retrieved_chunk_ids: list[str],
        final_output: dict,
    ) -> AuditLog:
        log = AuditLog(
            request_id=request_id,
            user_role=user_role,
            model_version=model_version,
            retriever_version=retriever_version,
            retrieved_chunk_ids=",".join(retrieved_chunk_ids),
            final_output=dumps(final_output),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_logs(self) -> list[AuditLog]:
        return self.db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()
