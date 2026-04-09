from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.documents import Document
from app.rag.ingestion import ingest_file_to_store, reindex_documents
from app.schemas.documents import DocumentRead


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    async def upload_and_index(
        self,
        title: str,
        organization: str,
        pathway: str,
        version_date: str,
        jurisdiction: str,
        approved_for_use: bool,
        upload: UploadFile,
    ) -> DocumentRead:
        protocols_dir = self.settings.protocols_path
        protocols_dir.mkdir(parents=True, exist_ok=True)
        target_path = protocols_dir / upload.filename
        content = await upload.read()
        target_path.write_bytes(content)

        document = Document(
            title=title,
            source_path=str(target_path),
            source_type=Path(upload.filename).suffix.replace(".", "") or "txt",
            organization=organization,
            pathway=pathway,
            version_date=date.fromisoformat(version_date),
            jurisdiction=jurisdiction,
            approved_for_use=approved_for_use,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        ingest_file_to_store(self.db, document)
        return DocumentRead.model_validate(document)

    def reindex_all(self) -> int:
        documents = self.db.query(Document).all()
        reindex_documents(self.db, documents)
        return len(documents)
