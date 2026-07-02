from sqlmodel import Session

from backend.app.db.engine import get_engine, init_db
from backend.app.db.fts import rebuild_document_fts, search_document_chunks
from backend.app.db.models import Chunk, Document, SourceType
from backend.app.services.chunker import chunk_section_text


def test_chunk_section_text_preserves_section_label():
    chunks = chunk_section_text(
        document_id="doc1",
        section_id="sec1",
        section_label="3.2 Training",
        text="Sentence one. Sentence two. Sentence three.",
        page_start=5,
        page_end=6,
        max_chars=25,
    )

    assert len(chunks) >= 2
    assert all(chunk.section_label == "3.2 Training" for chunk in chunks)


def test_fts_search_returns_relevant_chunk():
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        document = Document(title="Demo", source_type=SourceType.UPLOADED_PDF)
        session.add(document)
        session.commit()
        session.refresh(document)
        chunk = Chunk(
            document_id=document.id,
            section_label="2 Method",
            order=0,
            text="The proposed method improves baseline accuracy with ablation evidence.",
        )
        session.add(chunk)
        session.commit()
        session.refresh(chunk)

        rebuild_document_fts(session, document.id)
        results = search_document_chunks(session, document.id, "baseline ablation")

    assert len(results) == 1
    assert results[0].chunk_id == chunk.id
    assert "baseline accuracy" in results[0].text
