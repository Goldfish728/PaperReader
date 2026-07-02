from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.app.db.models import ChatRole, DocumentStatus, NoteKind, SourceType


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


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Question must not be blank.")
        return stripped


class RelatedChunkRead(BaseModel):
    chunk_id: str
    section_label: str | None
    page_start: int | None
    page_end: int | None
    text: str


class ChatResponse(BaseModel):
    answer: str
    related_chunks: list[RelatedChunkRead] = Field(default_factory=list)


class ChatMessageRead(BaseModel):
    id: str
    document_id: str
    role: ChatRole
    content: str
    related_chunks: list[RelatedChunkRead] = Field(default_factory=list)
    created_at: datetime
