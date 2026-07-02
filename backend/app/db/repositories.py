import json
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, select

from backend.app.db.fts import init_fts
from backend.app.db.models import (
    AppSetting,
    AssetKind,
    ChatMessage,
    ChatRole,
    Chunk,
    Document,
    DocumentAsset,
    DocumentStatus,
    Figure,
    Note,
    NoteKind,
    Section,
    SourceType,
    utc_now,
)


class SettingsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_value(self, key: str) -> str | None:
        setting = self.session.get(AppSetting, key)
        return setting.value if setting else None

    def set_value(self, key: str, value: str) -> None:
        setting = self.session.get(AppSetting, key)
        if setting is None:
            setting = AppSetting(key=key, value=value)
            self.session.add(setting)
        else:
            if setting.value != value:
                setting.value = value
                setting.updated_at = utc_now()
            self.session.add(setting)

    def list_all(self) -> dict[str, str]:
        rows = self.session.exec(select(AppSetting)).all()
        return {row.key: row.value for row in rows}


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_document(
        self,
        *,
        title: str,
        source_type: SourceType,
        original_url: str | None = None,
        document_id: str | None = None,
        commit: bool = True,
    ) -> Document:
        values = {
            "title": title,
            "source_type": source_type,
            "original_url": original_url,
            "status": DocumentStatus.QUEUED,
        }
        if document_id is not None:
            values["id"] = document_id
        document = Document(**values)
        self.session.add(document)
        if commit:
            self.session.commit()
            self.session.refresh(document)
        else:
            self.session.flush()
        return document

    def list_documents(self) -> list[Document]:
        return list(self.session.exec(select(Document).order_by(Document.created_at.desc())).all())

    def get_document(self, document_id: str) -> Document | None:
        return self.session.get(Document, document_id)

    def delete_document(self, document_id: str) -> bool:
        document = self.session.get(Document, document_id)
        if document is None:
            return False
        for model in (ChatMessage, Note, Chunk, Section, Figure, DocumentAsset):
            rows = self.session.exec(
                select(model).where(model.document_id == document_id)
            ).all()
            for row in rows:
                self.session.delete(row)
        init_fts(self.session, commit=False)
        self.session.execute(
            text("DELETE FROM chunks_fts WHERE document_id = :document_id"),
            {"document_id": document_id},
        )
        self.session.delete(document)
        self.session.commit()
        return True

    def update_status(
        self,
        document: Document,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> Document:
        document.status = status
        document.error_message = error_message
        document.updated_at = utc_now()
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document


class AssetRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_asset(
        self,
        *,
        document_id: str,
        kind: AssetKind,
        path: str,
        label: str | None = None,
        commit: bool = True,
    ) -> DocumentAsset:
        asset = DocumentAsset(
            document_id=document_id,
            kind=kind,
            path=path,
            label=label,
        )
        self.session.add(asset)
        if commit:
            self.session.commit()
            self.session.refresh(asset)
        else:
            self.session.flush()
        return asset


class SectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_sections(self, document_id: str, parsed_sections) -> list[Section]:
        existing = self.session.exec(
            select(Section).where(Section.document_id == document_id)
        ).all()
        for row in existing:
            self.session.delete(row)
        created: list[Section] = []
        for parsed in parsed_sections:
            section = Section(
                document_id=document_id,
                number=parsed.number,
                title=parsed.title,
                level=parsed.level,
                order=parsed.order,
                page_start=parsed.page_start,
                page_end=parsed.page_end,
                text=parsed.text,
            )
            self.session.add(section)
            created.append(section)
        self.session.commit()
        return created


class FigureRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_figures(self, document_id: str, extracted_figures) -> list[Figure]:
        existing = self.session.exec(
            select(Figure).where(Figure.document_id == document_id)
        ).all()
        for row in existing:
            self.session.delete(row)
        created: list[Figure] = []
        for item in extracted_figures:
            figure = Figure(
                document_id=document_id,
                label=item.label,
                caption=item.caption,
                page=item.page,
                image_path=str(item.image_path),
                order=item.order,
            )
            self.session.add(figure)
            created.append(figure)
        self.session.commit()
        return created


class ChunkRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_chunks(self, document_id: str, chunk_drafts) -> list[Chunk]:
        existing = self.session.exec(
            select(Chunk).where(Chunk.document_id == document_id)
        ).all()
        for row in existing:
            self.session.delete(row)
        created: list[Chunk] = []
        for draft in chunk_drafts:
            chunk = Chunk(
                document_id=draft.document_id,
                section_id=draft.section_id,
                section_label=draft.section_label,
                page_start=draft.page_start,
                page_end=draft.page_end,
                order=draft.order,
                text=draft.text,
            )
            self.session.add(chunk)
            created.append(chunk)
        self.session.commit()
        return created


class NoteRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_note(
        self,
        *,
        document_id: str,
        kind: NoteKind,
        markdown: str,
        path: str,
    ) -> Note:
        existing = self.session.exec(
            select(Note).where(Note.document_id == document_id, Note.kind == kind)
        ).all()
        for row in existing:
            self.session.delete(row)
        note = Note(document_id=document_id, kind=kind, markdown=markdown, path=path)
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def get_note(self, document_id: str, kind: NoteKind) -> Note | None:
        return self.session.exec(
            select(Note).where(Note.document_id == document_id, Note.kind == kind)
        ).first()


class ChatRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_message(
        self,
        document_id: str,
        role: ChatRole | str,
        content: str,
        related_chunks: Iterable[Any] | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            document_id=document_id,
            role=ChatRole(role),
            content=content,
            related_chunks_json=json.dumps(
                [_to_related_chunk_dict(item) for item in related_chunks or []],
                ensure_ascii=False,
            ),
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def list_messages(self, document_id: str) -> list[ChatMessage]:
        return list(
            self.session.exec(
                select(ChatMessage)
                .where(ChatMessage.document_id == document_id)
                .order_by(ChatMessage.created_at.asc())
            ).all()
        )


def _to_related_chunk_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if is_dataclass(item):
        return asdict(item)
    return {
        field: getattr(item, field)
        for field in ("chunk_id", "section_label", "page_start", "page_end", "text")
    }
