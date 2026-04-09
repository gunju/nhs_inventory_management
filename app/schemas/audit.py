from datetime import datetime

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: str
    request_id: str
    user_role: str
    model_version: str
    retriever_version: str
    retrieved_chunk_ids: str
    final_output: str
    accepted: bool | None
    override_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
