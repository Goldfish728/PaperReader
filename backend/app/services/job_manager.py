from pathlib import Path

from sqlmodel import Session

from backend.app.core.paths import document_dir
from backend.app.db.fts import rebuild_document_fts
from backend.app.db.models import Document, DocumentStatus, NoteKind
from backend.app.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    FigureRepository,
    NoteRepository,
    SectionRepository,
)
from backend.app.services.chunker import chunk_section_text
from backend.app.services.figure_extractor import extract_pdf_figures
from backend.app.services.html_parser import parse_html_article
from backend.app.services.model_client import ModelClient
from backend.app.services.note_generator import generate_notes
from backend.app.services.pdf_parser import parse_pdf


def mark_failed(session: Session, document: Document, message: str) -> None:
    DocumentRepository(session).update_status(
        document,
        DocumentStatus.FAILED,
        error_message=message,
    )


def set_status(session: Session, document: Document, status: DocumentStatus) -> None:
    DocumentRepository(session).update_status(document, status, error_message=None)


def persist_generated_notes(
    *,
    session: Session,
    document_id: str,
    structured_markdown: str,
    structured_path: Path,
    deep_markdown: str,
    deep_path: Path,
) -> None:
    repo = NoteRepository(session)
    repo.replace_note(
        document_id=document_id,
        kind=NoteKind.STRUCTURED_READING,
        markdown=structured_markdown,
        path=str(structured_path),
    )
    repo.replace_note(
        document_id=document_id,
        kind=NoteKind.DEEP_READING,
        markdown=deep_markdown,
        path=str(deep_path),
    )


async def process_existing_source(
    *,
    session: Session,
    document: Document,
    source_path: Path,
    model_client: ModelClient,
) -> None:
    try:
        set_status(session, document, DocumentStatus.PARSING)
        if source_path.suffix.lower() == ".pdf":
            parsed = parse_pdf(source_path)
            set_status(session, document, DocumentStatus.EXTRACTING_FIGURES)
            extracted_figures = extract_pdf_figures(document.id, source_path)
        else:
            parsed = parse_html_article(source_path)
            extracted_figures = []

        section_rows = SectionRepository(session).replace_sections(
            document.id,
            parsed.sections,
        )
        FigureRepository(session).replace_figures(document.id, extracted_figures)

        chunk_drafts = []
        for section_row in section_rows:
            chunk_drafts.extend(
                chunk_section_text(
                    document_id=document.id,
                    section_id=section_row.id,
                    section_label=_section_label(section_row.number, section_row.title),
                    text=section_row.text,
                    page_start=section_row.page_start,
                    page_end=section_row.page_end,
                )
            )
        ChunkRepository(session).replace_chunks(document.id, chunk_drafts)

        set_status(session, document, DocumentStatus.GENERATING_STRUCTURED_READING)
        set_status(session, document, DocumentStatus.GENERATING_DEEP_READING)
        notes = await generate_notes(
            document_id=document.id,
            parsed=parsed,
            figures=extracted_figures,
            output_dir=document_dir(document.id),
            model_client=model_client,
        )
        persist_generated_notes(
            session=session,
            document_id=document.id,
            structured_markdown=notes.structured_markdown,
            structured_path=notes.structured_path,
            deep_markdown=notes.deep_markdown,
            deep_path=notes.deep_path,
        )

        set_status(session, document, DocumentStatus.INDEXING)
        rebuild_document_fts(session, document.id)
        set_status(session, document, DocumentStatus.COMPLETED)
    except Exception as exc:
        mark_failed(session, document, str(exc))


def _section_label(number: str | None, title: str) -> str:
    if number and title.startswith(number):
        return title
    if number:
        return f"{number} {title}"
    return title
