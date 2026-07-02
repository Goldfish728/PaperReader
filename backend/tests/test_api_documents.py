from fastapi.testclient import TestClient

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

    response = client.post(
        "/api/documents/upload",
        files={"file": ("paper.pdf", b"%PDF-1.7\nfake pdf bytes", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "uploaded_pdf"
    assert body["status"] == "queued"
    assert body["title"] == "paper.pdf"


def test_upload_rejects_non_pdf():
    client = TestClient(create_app())

    response = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF uploads are supported in this version."
