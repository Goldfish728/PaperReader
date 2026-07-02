import json
import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from backend.app.core.config import get_settings
from backend.app.db.engine import get_session
from backend.app.db.models import AssetKind, ChatMessage, ChatRole, NoteKind, SourceType, new_id
from backend.app.db.repositories import (
    AssetRepository,
    ChatRepository,
    DocumentRepository,
    NoteRepository,
    SettingsRepository,
)
from backend.app.schemas.documents import (
    ChatMessageRead,
    ChatRequest,
    ChatResponse,
    DocumentRead,
    ImportUrlRequest,
    NoteRead,
    RelatedChunkRead,
)
from backend.app.services.chat_engine import answer_question
from backend.app.services.fetcher import save_uploaded_pdf
from backend.app.services.model_client import ModelClient
from backend.app.services.source_detector import detect_text_source

router = APIRouter(prefix="/api/documents", tags=["documents"])
SessionDependency = Annotated[Session, Depends(get_session)]
UploadFileDependency = Annotated[UploadFile, File(...)]


@router.get("", response_model=list[DocumentRead])
def list_documents(session: SessionDependency) -> list[DocumentRead]:
    return DocumentRepository(session).list_documents()


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, session: SessionDependency) -> DocumentRead:
    document = DocumentRepository(session).get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.get("/{document_id}/notes/{kind}", response_model=NoteRead)
def get_note(
    document_id: str,
    kind: NoteKind,
    session: SessionDependency,
) -> NoteRead:
    note = NoteRepository(session).get_note(document_id, kind)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    return NoteRead(document_id=document_id, kind=kind, markdown=note.markdown)


@router.get("/{document_id}/chat", response_model=list[ChatMessageRead])
def list_chat(document_id: str, session: SessionDependency) -> list[ChatMessageRead]:
    messages = ChatRepository(session).list_messages(document_id)
    return [_message_to_read(message) for message in messages]


@router.post("/{document_id}/chat", response_model=ChatResponse)
async def chat(
    document_id: str,
    payload: ChatRequest,
    session: SessionDependency,
) -> ChatResponse:
    document = DocumentRepository(session).get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    ChatRepository(session).add_message(
        document_id=document_id,
        role=ChatRole.USER,
        content=payload.question,
    )
    result = await answer_question(
        session=session,
        document_id=document_id,
        question=payload.question,
        model_client=_model_client_from_settings(session),
    )
    related_chunks = [_related_chunk_to_read(chunk) for chunk in result.related_chunks]
    ChatRepository(session).add_message(
        document_id=document_id,
        role=ChatRole.ASSISTANT,
        content=result.answer,
        related_chunks=[chunk.model_dump() for chunk in related_chunks],
    )
    return ChatResponse(answer=result.answer, related_chunks=related_chunks)


@router.post("/import-url", response_model=DocumentRead)
def import_url(payload: ImportUrlRequest, session: SessionDependency) -> DocumentRead:
    detected = detect_text_source(payload.value)
    title = detected.normalized_value
    original_url = (
        payload.value if detected.source_type == SourceType.ARXIV else detected.normalized_value
    )
    return DocumentRepository(session).create_document(
        title=title,
        source_type=detected.source_type,
        original_url=original_url,
    )


@router.post("/upload", response_model=DocumentRead)
async def upload_pdf(file: UploadFileDependency, session: SessionDependency) -> DocumentRead:
    document_id = new_id()
    try:
        path = await save_uploaded_pdf(document_id, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        document = DocumentRepository(session).create_document(
            document_id=document_id,
            title=file.filename or "uploaded.pdf",
            source_type=SourceType.UPLOADED_PDF,
            original_url=None,
            commit=False,
        )
        AssetRepository(session).create_asset(
            document_id=document.id,
            kind=AssetKind.ORIGINAL_PDF,
            path=str(path),
            label="Original PDF",
            commit=False,
        )
        session.commit()
    except Exception:
        session.rollback()
        shutil.rmtree(path.parent, ignore_errors=True)
        raise

    session.refresh(document)
    return document


def _model_client_from_settings(session: Session) -> ModelClient:
    env = get_settings()
    values = SettingsRepository(session).list_all()
    return ModelClient(
        base_url=values.get("api_base_url", env.api_base_url),
        api_key=values.get("api_key", env.api_key),
        model=values.get("chat_model", env.chat_model),
        timeout_seconds=int(
            values.get("request_timeout_seconds", env.request_timeout_seconds)
        ),
        temperature=float(values.get("temperature", env.temperature)),
    )


def _message_to_read(message: ChatMessage) -> ChatMessageRead:
    try:
        raw_chunks = json.loads(message.related_chunks_json)
    except json.JSONDecodeError:
        raw_chunks = []
    return ChatMessageRead(
        id=message.id,
        document_id=message.document_id,
        role=message.role,
        content=message.content,
        related_chunks=[
            _related_chunk_to_read(chunk)
            for chunk in raw_chunks
            if isinstance(chunk, dict)
        ],
        created_at=message.created_at,
    )


def _related_chunk_to_read(chunk) -> RelatedChunkRead:
    if isinstance(chunk, dict):
        data = chunk
    elif hasattr(chunk, "model_dump"):
        data = chunk.model_dump()
    else:
        data = {
            "chunk_id": chunk.chunk_id,
            "section_label": chunk.section_label,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "text": chunk.text,
        }
    return RelatedChunkRead(**data)
