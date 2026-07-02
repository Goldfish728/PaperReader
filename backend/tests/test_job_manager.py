from sqlmodel import Session

from backend.app.db.engine import get_engine, init_db
from backend.app.db.models import Document, DocumentStatus, SourceType
from backend.app.services.job_manager import mark_failed


def test_mark_failed_records_error_message():
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        document = Document(title="Demo", source_type=SourceType.UPLOADED_PDF)
        session.add(document)
        session.commit()
        session.refresh(document)

        mark_failed(session, document, "PDF has no extractable text.")

        session.refresh(document)
        assert document.status == DocumentStatus.FAILED
        assert document.error_message == "PDF has no extractable text."
