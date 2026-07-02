from pathlib import Path

from backend.app.core.config import get_settings


def _safe_document_id(document_id: str) -> str:
    if (
        not document_id
        or document_id in {".", ".."}
        or Path(document_id).is_absolute()
        or ".." in Path(document_id).parts
        or "/" in document_id
        or "\\" in document_id
    ):
        raise ValueError("document_id must be a single safe path segment")
    return document_id


def data_dir() -> Path:
    root = get_settings().data_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def document_dir(document_id: str) -> Path:
    path = data_dir() / "documents" / _safe_document_id(document_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def figures_dir(document_id: str) -> Path:
    path = document_dir(document_id) / "figures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "app.db"
