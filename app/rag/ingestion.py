"""
Document ingestion pipeline: upload → parse → chunk → embed → store.
"""
from __future__ import annotations

import os
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import log
from app.models.rag import DocumentChunk, DocumentSource, EmbeddingIndexRef
from app.rag.chunker import Chunk, chunk_text, extract_text_from_file
from app.rag.embedder import get_embedder

settings = get_settings()


class DocumentIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedder = get_embedder()

    def ingest(
        self,
        file_path: str,
        filename: str,
        doc_type: str,
        trust_id: uuid.UUID | None = None,
        uploaded_by_id: uuid.UUID | None = None,
        mime_type: str | None = None,
    ) -> DocumentSource:
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        source = DocumentSource(
            trust_id=trust_id,
            uploaded_by_id=uploaded_by_id,
            filename=filename,
            doc_type=doc_type,
            storage_path=file_path,
            mime_type=mime_type,
            file_size_bytes=file_size,
            is_indexed=False,
        )
        self.db.add(source)
        self.db.flush()

        try:
            text = extract_text_from_file(file_path, mime_type)
            chunks = chunk_text(text)
            self._index_chunks(source, chunks, trust_id)
            source.is_indexed = True
            log.info("document_indexed", source_id=str(source.id), chunks=len(chunks))
        except Exception as exc:
            source.index_error = str(exc)
            log.error("document_index_failed", source_id=str(source.id), error=str(exc))

        self.db.commit()
        return source

    def _index_chunks(
        self, source: DocumentSource, chunks: list[Chunk], trust_id: uuid.UUID | None
    ) -> None:
        texts = [c.content for c in chunks]
        if not texts:
            return
        embeddings = self.embedder.embed_batch(texts)

        for chunk, embedding in zip(chunks, embeddings):
            db_chunk = DocumentChunk(
                source_id=source.id,
                trust_id=trust_id,
                chunk_index=chunk.index,
                content=chunk.content,
                token_count=chunk.token_estimate,
                page_number=chunk.page_number,
            )
            self.db.add(db_chunk)
            self.db.flush()

            ref = EmbeddingIndexRef(
                chunk_id=db_chunk.id,
                trust_id=trust_id,
                model_name=(
                    settings.openai_embedding_model
                    if settings.embedding_provider == "openai"
                    else "mock"
                ),
                vector_dim=len(embedding),
                embedding=embedding,
            )
            self.db.add(ref)
        self.db.flush()
