from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.app.core.paths import data_dir
from backend.app.db.engine import get_engine
from backend.app.db.models import AssetKind, ChatMessage, Document, DocumentAsset
from backend.app.db.repositories import AssetRepository
from backend.app.main import create_app


def test_import_url_creates_queued_document():
    client = TestClient(create_app())

    response = client.post("/api/documents/import-url", json={"value": "2401.12345"})

    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "arxiv"
    assert body["status"] == "queued"
    assert body["title"] == "2401.12345"


def test_import_url_rejects_whitespace_only_value():
    client = TestClient(create_app())

    response = client.post("/api/documents/import-url", json={"value": "   "})

    assert response.status_code == 422


def test_import_url_strips_value_before_detection_and_persistence():
    client = TestClient(create_app())

    response = client.post("/api/documents/import-url", json={"value": "  2401.12345  "})

    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "arxiv"
    assert body["title"] == "2401.12345"
    assert body["original_url"] == "2401.12345"


def test_import_url_persists_normalized_non_arxiv_values():
    client = TestClient(create_app())

    response = client.post(
        "/api/documents/import-url",
        json={"value": "  https://example.com/paper.pdf#page=2  "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "pdf_url"
    assert body["title"] == "https://example.com/paper.pdf#page=2"
    assert body["original_url"] == "https://example.com/paper.pdf#page=2"


def test_list_documents_returns_created_document():
    client = TestClient(create_app())
    client.post("/api/documents/import-url", json={"value": "https://example.com/paper.pdf"})

    response = client.get("/api/documents")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["source_type"] == "pdf_url"


def test_upload_pdf_creates_document():
    client = TestClient(create_app())
    pdf_bytes = b"%PDF-1.7\nfake pdf bytes"

    response = client.post(
        "/api/documents/upload",
        files={"file": ("paper.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "uploaded_pdf"
    assert body["status"] == "queued"
    assert body["title"] == "paper.pdf"

    with Session(get_engine()) as session:
        assets = session.exec(select(DocumentAsset)).all()

    assert len(assets) == 1
    asset = assets[0]
    assert asset.document_id == body["id"]
    assert asset.kind == AssetKind.ORIGINAL_PDF
    assert asset.path.endswith("original.pdf")
    assert asset.label == "Original PDF"
    assert asset.path and asset.path.endswith(f"{body['id']}/original.pdf")
    asset_path = Path(asset.path)
    assert data_dir() in asset_path.parents
    assert asset_path.read_bytes() == pdf_bytes


def test_upload_rejects_non_pdf():
    client = TestClient(create_app())

    response = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF uploads are supported in this version."


def test_upload_rejects_pdf_filename_with_non_pdf_bytes_without_persisting():
    client = TestClient(create_app())

    response = client.post(
        "/api/documents/upload",
        files={"file": ("paper.pdf", b"not actually a pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file does not look like a PDF."

    with Session(get_engine()) as session:
        assert session.exec(select(Document)).all() == []
        assert session.exec(select(DocumentAsset)).all() == []

    documents_root = data_dir() / "documents"
    assert not documents_root.exists() or list(documents_root.iterdir()) == []


def test_upload_rolls_back_document_and_file_when_asset_creation_fails(monkeypatch):
    def fail_create_asset(self, **kwargs):
        raise RuntimeError("asset insert failed")

    monkeypatch.setattr(AssetRepository, "create_asset", fail_create_asset)
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("paper.pdf", b"%PDF-1.7\nfake pdf bytes", "application/pdf")},
    )

    assert response.status_code == 500

    with Session(get_engine()) as session:
        assert session.exec(select(Document)).all() == []
        assert session.exec(select(DocumentAsset)).all() == []

    documents_root = data_dir() / "documents"
    assert not documents_root.exists() or list(documents_root.iterdir()) == []


def test_get_document_detail():
    client = TestClient(create_app())
    created = client.post("/api/documents/import-url", json={"value": "2401.12345"}).json()

    response = client.get(f"/api/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_missing_note_returns_404():
    client = TestClient(create_app())
    created = client.post("/api/documents/import-url", json={"value": "2401.12345"}).json()

    response = client.get(f"/api/documents/{created['id']}/notes/structured_reading")

    assert response.status_code == 404


def test_list_chat_history_returns_saved_messages():
    client = TestClient(create_app())
    created = client.post("/api/documents/import-url", json={"value": "2401.12345"}).json()

    response = client.get(f"/api/documents/{created['id']}/chat")

    assert response.status_code == 200
    assert response.json() == []


def test_post_chat_returns_404_for_missing_document():
    client = TestClient(create_app())

    response = client.post(
        "/api/documents/missing-document/chat",
        json={"question": "这篇论文的方法是什么？"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_post_chat_saves_user_and_assistant_messages(monkeypatch):
    async def fake_answer_question(session, document_id, question, model_client):
        return SimpleNamespace(
            answer=f"回答：{question}",
            related_chunks=[
                SimpleNamespace(
                    chunk_id="chunk-1",
                    section_label="2 Method",
                    page_start=3,
                    page_end=4,
                    text="The method uses a retrieval grounded approach.",
                )
            ],
        )

    monkeypatch.setattr(
        "backend.app.api.documents.answer_question",
        fake_answer_question,
    )
    client = TestClient(create_app())
    created = client.post("/api/documents/import-url", json={"value": "2401.12345"}).json()

    response = client.post(
        f"/api/documents/{created['id']}/chat",
        json={"question": "方法是什么？"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "回答：方法是什么？"
    assert body["related_chunks"][0]["section_label"] == "2 Method"

    history_response = client.get(f"/api/documents/{created['id']}/chat")

    assert history_response.status_code == 200
    messages = history_response.json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "方法是什么？"
    assert messages[1]["content"] == "回答：方法是什么？"
    assert messages[1]["related_chunks"][0]["section_label"] == "2 Method"


def test_delete_document_removes_it_from_list_and_related_rows():
    client = TestClient(create_app())
    created = client.post("/api/documents/import-url", json={"value": "2401.12345"}).json()
    with Session(get_engine()) as session:
        session.add(
            ChatMessage(
                document_id=created["id"],
                role="user",
                content="这篇论文的方法是什么？",
            )
        )
        session.commit()

    response = client.delete(f"/api/documents/{created['id']}")

    assert response.status_code == 204
    assert client.get("/api/documents").json() == []
    with Session(get_engine()) as session:
        assert session.exec(select(ChatMessage)).all() == []
