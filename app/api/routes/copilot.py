"""Copilot chat and document upload endpoints."""
from __future__ import annotations

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.middleware.auth import CurrentUser
from app.copilot.service import CopilotService
from app.db.session import get_db
from app.models.rag import ConversationSession
from app.rag.ingestion import DocumentIngestionService
from app.schemas.copilot import ChatRequest, ConversationOut, CopilotResponse
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

ALLOWED_MIME_TYPES = {"application/pdf", "text/plain", "text/markdown"}
MAX_FILE_MB = 20


@router.post("/chat", response_model=CopilotResponse, summary="Operational Q&A copilot")
def chat(
    body: ChatRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CopilotResponse:
    trust_id = body.trust_id or current_user.trust_id
    if not trust_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"code": "MISSING_TRUST_ID", "message": "trust_id required"})
    svc = CopilotService(db)
    return svc.chat(
        question=body.message,
        trust_id=trust_id,
        user_id=current_user.id,
        session_id=body.session_id,
    )


@router.get("/conversations/{session_id}", response_model=ConversationOut)
def get_conversation(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ConversationOut:
    session = db.get(ConversationSession, session_id)
    if not session or session.trust_id != current_user.trust_id:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Session not found"})
    msgs = [{"role": m.role, "content": m.content, "sequence": m.sequence}
            for m in sorted(session.messages, key=lambda x: x.sequence)]
    return ConversationOut(
        id=session.id,
        title=session.title,
        is_active=session.is_active,
        created_at=session.created_at.isoformat(),
        messages=msgs,
    )


@router.post("/documents/upload", summary="Upload SOP/policy document for RAG indexing")
async def upload_document(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    doc_type: str = Form(default="SOP"),
) -> dict:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "UNSUPPORTED_FILE_TYPE", "message": f"Allowed: {ALLOWED_MIME_TYPES}"},
        )
    content = await file.read()
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": f"Max {MAX_FILE_MB}MB"},
        )
    upload_dir = os.path.join(settings.storage_local_path, str(current_user.trust_id or "global"))
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    svc = DocumentIngestionService(db)
    source = svc.ingest(
        file_path=file_path,
        filename=file.filename or safe_name,
        doc_type=doc_type,
        trust_id=current_user.trust_id,
        uploaded_by_id=current_user.id,
        mime_type=file.content_type,
    )
    return {
        "document_id": str(source.id),
        "filename": source.filename,
        "is_indexed": source.is_indexed,
        "error": source.index_error,
    }
