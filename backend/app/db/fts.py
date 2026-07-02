from dataclasses import dataclass

from sqlalchemy import text
from sqlmodel import Session


@dataclass(frozen=True)
class FtsSearchResult:
    chunk_id: str
    section_label: str | None
    page_start: int | None
    page_end: int | None
    text: str
    rank: float


def init_fts(session: Session, *, commit: bool = True) -> None:
    session.execute(
        text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(chunk_id UNINDEXED, document_id UNINDEXED, section_label, text)
            """
        )
    )
    if commit:
        _commit_without_expiring(session)


def rebuild_document_fts(session: Session, document_id: str) -> None:
    init_fts(session, commit=False)
    session.execute(
        text("DELETE FROM chunks_fts WHERE document_id = :document_id"),
        {"document_id": document_id},
    )
    rows = session.execute(
        text(
            """
            SELECT id, document_id, section_label, text
            FROM chunk
            WHERE document_id = :document_id
            ORDER BY "order"
            """
        ),
        {"document_id": document_id},
    ).mappings()
    for row in rows:
        session.execute(
            text(
                """
                INSERT INTO chunks_fts(chunk_id, document_id, section_label, text)
                VALUES (:chunk_id, :document_id, :section_label, :text)
                """
            ),
            {
                "chunk_id": row["id"],
                "document_id": row["document_id"],
                "section_label": row["section_label"] or "",
                "text": row["text"],
            },
        )
    _commit_without_expiring(session)


def search_document_chunks(
    session: Session,
    document_id: str,
    query: str,
    limit: int = 8,
) -> list[FtsSearchResult]:
    init_fts(session, commit=False)
    safe_query = " ".join(token for token in query.replace('"', " ").split() if token)
    if not safe_query:
        return []
    rows = session.execute(
        text(
            """
            SELECT
              c.id AS chunk_id,
              c.section_label AS section_label,
              c.page_start AS page_start,
              c.page_end AS page_end,
              c.text AS text,
              bm25(chunks_fts) AS rank
            FROM chunks_fts
            JOIN chunk c ON c.id = chunks_fts.chunk_id
            WHERE chunks_fts MATCH :query
              AND chunks_fts.document_id = :document_id
            ORDER BY rank
            LIMIT :limit
            """
        ),
        {"query": safe_query, "document_id": document_id, "limit": limit},
    ).mappings()
    return [
        FtsSearchResult(
            chunk_id=row["chunk_id"],
            section_label=row["section_label"],
            page_start=row["page_start"],
            page_end=row["page_end"],
            text=row["text"],
            rank=row["rank"],
        )
        for row in rows
    ]


def _commit_without_expiring(session: Session) -> None:
    old_expire_on_commit = session.expire_on_commit
    session.expire_on_commit = False
    try:
        session.commit()
    finally:
        session.expire_on_commit = old_expire_on_commit
