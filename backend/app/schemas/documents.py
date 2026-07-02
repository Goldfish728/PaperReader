from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.db.models import DocumentStatus, SourceType


class ImportUrlRequest(BaseModel):
    value: str = Field(min_length=1)


class DocumentRead(BaseModel):
    id: str
    title: str
    source_type: SourceType
    original_url: str | None
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
