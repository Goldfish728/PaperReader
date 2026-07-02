from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.app.db.models import DocumentStatus, NoteKind, SourceType


class ImportUrlRequest(BaseModel):
    value: str = Field(min_length=1)

    @field_validator("value")
    @classmethod
    def strip_value(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be blank.")
        return stripped


class DocumentRead(BaseModel):
    id: str
    title: str
    source_type: SourceType
    original_url: str | None
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class NoteRead(BaseModel):
    document_id: str
    kind: NoteKind
    markdown: str
