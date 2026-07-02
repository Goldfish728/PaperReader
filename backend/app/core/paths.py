from pathlib import Path

from backend.app.core.config import get_settings


def data_dir() -> Path:
    root = get_settings().data_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def document_dir(document_id: str) -> Path:
    path = data_dir() / "documents" / document_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def figures_dir(document_id: str) -> Path:
    path = document_dir(document_id) / "figures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "app.db"
