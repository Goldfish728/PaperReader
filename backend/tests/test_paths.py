import pytest

from backend.app.core.paths import document_dir


def test_document_dir_creates_directory_under_documents(tmp_path) -> None:
    path = document_dir("paper-123")

    assert path == tmp_path / "data" / "documents" / "paper-123"
    assert path.is_dir()


@pytest.mark.parametrize(
    "document_id",
    [
        "../escape",
        "/tmp/escape",
        "nested/id",
        "",
        r"nested\id",
    ],
)
def test_document_dir_rejects_unsafe_document_ids(document_id: str) -> None:
    with pytest.raises(ValueError):
        document_dir(document_id)
