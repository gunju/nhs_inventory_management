from datetime import date, datetime

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    title: str
    source_path: str
    source_type: str
    organization: str
    pathway: str
    version_date: date
    jurisdiction: str = "UK"
    approved_for_use: bool = True


class DocumentRead(DocumentCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}
