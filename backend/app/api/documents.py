from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.app.db.engine import get_session
from backend.app.db.models import SourceType
from backend.app.db.repositories import DocumentRepository
from backend.app.schemas.documents import DocumentRead, ImportUrlRequest
from backend.app.services.source_detector import detect_text_source

router = APIRouter(prefix="/api/documents", tags=["documents"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[DocumentRead])
def list_documents(session: SessionDependency) -> list[DocumentRead]:
    return DocumentRepository(session).list_documents()


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
