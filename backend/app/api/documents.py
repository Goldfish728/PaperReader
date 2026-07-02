import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from backend.app.db.engine import get_session
from backend.app.db.models import AssetKind, SourceType, new_id
from backend.app.db.repositories import AssetRepository, DocumentRepository
from backend.app.schemas.documents import DocumentRead, ImportUrlRequest
from backend.app.services.fetcher import save_uploaded_pdf
from backend.app.services.source_detector import detect_text_source

router = APIRouter(prefix="/api/documents", tags=["documents"])
SessionDependency = Annotated[Session, Depends(get_session)]
UploadFileDependency = Annotated[UploadFile, File(...)]


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
