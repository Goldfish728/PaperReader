from sqlmodel import Session

from backend.app.db.models import Document, DocumentStatus
from backend.app.db.repositories import DocumentRepository


def mark_failed(session: Session, document: Document, message: str) -> None:
    DocumentRepository(session).update_status(
        document,
        DocumentStatus.FAILED,
        error_message=message,
    )


def set_status(session: Session, document: Document, status: DocumentStatus) -> None:
    DocumentRepository(session).update_status(document, status, error_message=None)
