import pytest
from sqlmodel import Session, select

from backend.app.db.engine import get_engine, init_db
from backend.app.db.fts import search_document_chunks
from backend.app.db.models import Chunk, Document, DocumentStatus, Note, NoteKind, SourceType
from backend.app.services.job_manager import (
    mark_failed,
    persist_generated_notes,
    process_existing_source,
)
from backend.app.services.note_generator import GeneratedNotes
from backend.app.services.pdf_parser import ParsedDocument, ParsedSection


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


def test_persist_generated_notes_saves_both_notes(tmp_path):
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        document = Document(title="Demo", source_type=SourceType.UPLOADED_PDF)
        session.add(document)
        session.commit()
        session.refresh(document)
        structured = tmp_path / "structured_reading_note.md"
        deep = tmp_path / "deep_reading_note.md"

        persist_generated_notes(
            session=session,
            document_id=document.id,
            structured_markdown="# 全文理解",
            structured_path=structured,
            deep_markdown="# 整篇精读",
            deep_path=deep,
        )

        notes = session.exec(select(Note)).all()
        assert {note.kind for note in notes} == {
            NoteKind.STRUCTURED_READING,
            NoteKind.DEEP_READING,
        }


@pytest.mark.asyncio
async def test_process_existing_source_persists_notes_chunks_and_fts(monkeypatch, tmp_path):
    async def fake_generate_notes(
        *,
        document_id,
        parsed,
        figures,
        output_dir,
        model_client,
    ):
        structured_path = output_dir / "structured_reading_note.md"
        deep_path = output_dir / "deep_reading_note.md"
        structured_path.write_text("# 全文理解", encoding="utf-8")
        deep_path.write_text("# 整篇精读", encoding="utf-8")
        return GeneratedNotes(
            structured_markdown="# 全文理解",
            deep_markdown="# 整篇精读",
            structured_path=structured_path,
            deep_path=deep_path,
        )

    parsed = ParsedDocument(
        title="Demo Paper",
        raw_text="The method improves baseline accuracy with ablation evidence.",
        sections=[
            ParsedSection(
                number="2",
                title="Method",
                level=1,
                order=0,
                page_start=None,
                page_end=None,
                text="The method improves baseline accuracy with ablation evidence.",
            )
        ],
    )
    monkeypatch.setattr(
        "backend.app.services.job_manager.parse_html_article",
        lambda path: parsed,
    )
    monkeypatch.setattr(
        "backend.app.services.job_manager.generate_notes",
        fake_generate_notes,
    )

    init_db()
    engine = get_engine()
    with Session(engine) as session:
        document = Document(title="Demo", source_type=SourceType.HTML_ARTICLE)
        session.add(document)
        session.commit()
        session.refresh(document)
        source_path = tmp_path / "source.html"
        source_path.write_text("<article>placeholder</article>", encoding="utf-8")

        await process_existing_source(
            session=session,
            document=document,
            source_path=source_path,
            model_client=object(),
        )

        session.refresh(document)
        notes = session.exec(select(Note)).all()
        chunks = session.exec(select(Chunk)).all()
        search_results = search_document_chunks(
            session,
            document.id,
            "baseline ablation",
        )

        assert document.status == DocumentStatus.COMPLETED
        assert {note.kind for note in notes} == {
            NoteKind.STRUCTURED_READING,
            NoteKind.DEEP_READING,
        }
        assert chunks[0].section_label == "2 Method"
        assert search_results[0].chunk_id == chunks[0].id
