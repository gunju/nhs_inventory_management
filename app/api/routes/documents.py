from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.documents import DocumentRead
from app.services.document_service import DocumentService


router = APIRouter()


@router.post("/upload", response_model=DocumentRead)
async def upload_document(
    title: str = Form(...),
    organization: str = Form(...),
    pathway: str = Form(...),
    version_date: str = Form(...),
    jurisdiction: str = Form("UK"),
    approved_for_use: bool = Form(True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentRead:
    service = DocumentService(db)
    return await service.upload_and_index(
        title=title,
        organization=organization,
        pathway=pathway,
        version_date=version_date,
        jurisdiction=jurisdiction,
        approved_for_use=approved_for_use,
        upload=file,
    )


@router.post("/reindex")
def reindex_documents(db: Session = Depends(get_db)) -> dict[str, int]:
    service = DocumentService(db)
    count = service.reindex_all()
    return {"reindexed_documents": count}
