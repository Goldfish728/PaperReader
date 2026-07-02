from sqlmodel import Session, select

from backend.app.db.models import (
    AppSetting,
    AssetKind,
    Document,
    DocumentAsset,
    DocumentStatus,
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
