"""
RAG / LLM models: document sources, chunks, conversations, copilot answers.
pgvector embeddings stored here.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin, UUIDMixin

# pgvector VECTOR type — guarded import so app starts without pgvector extension during dev
try:
    from pgvector.sqlalchemy import Vector
    _VECTOR_TYPE = Vector
except ImportError:
    _VECTOR_TYPE = None  # type: ignore[assignment]


class DocumentSource(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document_sources"

    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)  # SOP, POLICY, SUPPLIER_NOTE, PLAYBOOK
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    index_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class DocumentChunk(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document_chunks"

    source_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("document_sources.id"), nullable=False, index=True)
    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["DocumentSource"] = relationship(back_populates="chunks")


class EmbeddingIndexRef(Base, UUIDMixin, TimestampMixin):
    """Reference linking a DocumentChunk to its vector index entry."""
    __tablename__ = "embedding_index_refs"

    chunk_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("document_chunks.id"), nullable=False, unique=True, index=True)
    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    vector_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    index_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Inline vector stored only when pgvector is available; else use external index
    embedding: Mapped[list[float] | None] = mapped_column(
        _VECTOR_TYPE(1536) if _VECTOR_TYPE else Text,  # type: ignore[call-arg]
        nullable=True,
    )


class ConversationSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversation_sessions"

    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    messages: Mapped[list["ConversationMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    answers: Mapped[list["CopilotAnswer"]] = relationship(back_populates="session")


class ConversationMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversation_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("conversation_sessions.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant / system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    session: Mapped["ConversationSession"] = relationship(back_populates="messages")


class CopilotAnswer(Base, UUIDMixin, TimestampMixin):
    """Structured output of a copilot Q&A turn."""
    __tablename__ = "copilot_answers"

    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("conversation_sessions.id"), nullable=False, index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("conversation_messages.id"), nullable=True)
    trust_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("trusts.id"), nullable=True, index=True)

    answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    reason_codes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of evidence refs
    recommended_actions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    follow_up_questions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    grounded: Mapped[bool] = mapped_column(Boolean, default=True)  # False = fallback used

    session: Mapped["ConversationSession"] = relationship(back_populates="answers")
