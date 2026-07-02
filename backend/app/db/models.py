from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlmodel import Field, SQLModel


def new_id() -> str:
    return uuid4().hex


def utc_now() -> datetime:
    return datetime.now(UTC)


class SourceType(StrEnum):
    UPLOADED_PDF = "uploaded_pdf"
    PDF_URL = "pdf_url"
    ARXIV = "arxiv"
    HTML_ARTICLE = "html_article"


class DocumentStatus(StrEnum):
    QUEUED = "queued"
    FETCHING = "fetching"
    PARSING = "parsing"
    EXTRACTING_FIGURES = "extracting_figures"
    GENERATING_STRUCTURED_READING = "generating_structured_reading"
    GENERATING_DEEP_READING = "generating_deep_reading"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class NoteKind(StrEnum):
    STRUCTURED_READING = "structured_reading"
    DEEP_READING = "deep_reading"


class AssetKind(StrEnum):
    ORIGINAL_PDF = "original_pdf"
    SOURCE_HTML = "source_html"
    FIGURE = "figure"
    NOTE = "note"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class Document(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    title: str = Field(default="Untitled")
    authors_json: str = Field(default="[]")
    source_type: SourceType
    original_url: str | None = None
    abstract: str | None = None
    status: DocumentStatus = Field(default=DocumentStatus.QUEUED, index=True)
    error_message: str | None = None
    model_snapshot_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DocumentAsset(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    kind: AssetKind
    path: str
    label: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Section(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    number: str | None = None
    title: str
    level: int = Field(default=1)
    parent_id: str | None = None
    order: int
    page_start: int | None = None
    page_end: int | None = None
    text: str = Field(default="")


class Chunk(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    section_id: str | None = Field(default=None, index=True)
    section_label: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    order: int
    text: str


class Figure(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    section_id: str | None = Field(default=None, index=True)
    label: str | None = None
    caption: str | None = None
    page: int | None = None
    image_path: str
    order: int


class Note(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    kind: NoteKind
    markdown: str
    path: str
    created_at: datetime = Field(default_factory=utc_now)


class ChatMessage(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    role: ChatRole
    content: str
    related_chunks_json: str = Field(default="[]")
    created_at: datetime = Field(default_factory=utc_now)


class AppSetting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str
    updated_at: datetime = Field(default_factory=utc_now)
