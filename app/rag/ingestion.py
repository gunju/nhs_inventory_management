from __future__ import annotations

from app.models.documents import Document as DocumentModel, DocumentChunk
from app.rag.langchain_pipeline import build_or_update_vector_store, load_source_documents, split_documents
from app.utils.json import dumps


def ingest_file_to_store(db, document: DocumentModel) -> None:
    raw_docs = load_source_documents(document.source_path)
    for doc in raw_docs:
        doc.metadata.update(
            {
                "doc_id": document.id,
                "source_type": document.source_type,
                "organization": document.organization,
                "pathway": document.pathway,
                "version_date": str(document.version_date),
                "jurisdiction": document.jurisdiction,
                "approved_for_use": document.approved_for_use,
                "url_or_path": document.source_path,
            }
        )
    chunks = split_documents(raw_docs)
    for idx, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{document.id}_chunk_{idx}"
    build_or_update_vector_store(chunks)
    for idx, chunk in enumerate(chunks):
        row = DocumentChunk(
            document_id=document.id,
            chunk_index=idx,
            content=chunk.page_content,
            metadata_json=dumps(chunk.metadata),
            embedding_ref=f"{document.id}:{idx}",
        )
        db.add(row)
    db.commit()


def reindex_documents(db, documents: list[DocumentModel]) -> None:
    db.query(DocumentChunk).delete()
    db.commit()
    for document in documents:
        ingest_file_to_store(db, document)
