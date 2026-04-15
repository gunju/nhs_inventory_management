"""
Document retriever — cosine similarity over stored embeddings.
Uses in-memory numpy similarity (pgvector upgrade path available).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import log
from app.models.rag import DocumentChunk, DocumentSource, EmbeddingIndexRef
from app.rag.embedder import get_embedder

settings = get_settings()


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    content: str
    source_filename: str
    score: float
    page_number: int | None = None


class DocumentRetriever:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedder = get_embedder()
        self.top_k = settings.rag_top_k

    def retrieve(self, query: str, trust_id: uuid.UUID | None = None) -> list[RetrievedChunk]:
        query_vec = np.array(self.embedder.embed(query), dtype=np.float32)

        stmt = (
            select(EmbeddingIndexRef, DocumentChunk, DocumentSource)
            .join(DocumentChunk, EmbeddingIndexRef.chunk_id == DocumentChunk.id)
            .join(DocumentSource, DocumentChunk.source_id == DocumentSource.id)
        )
        if trust_id:
            stmt = stmt.where(EmbeddingIndexRef.trust_id == trust_id)

        rows = self.db.execute(stmt).all()
        if not rows:
            return []

        scored: list[tuple[float, RetrievedChunk]] = []
        for ref, chunk, source in rows:
            if ref.embedding is None:
                continue
            try:
                vec = np.array(ref.embedding, dtype=np.float32)
                norm = np.linalg.norm(query_vec) * np.linalg.norm(vec)
                score = float(np.dot(query_vec, vec) / max(norm, 1e-9))
            except Exception:
                continue
            scored.append((score, RetrievedChunk(
                chunk_id=chunk.id,
                content=chunk.content,
                source_filename=source.filename,
                score=score,
                page_number=chunk.page_number,
            )))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [rc for _, rc in scored[:self.top_k]]
