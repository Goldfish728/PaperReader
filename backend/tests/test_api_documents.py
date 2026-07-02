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


def test_list_documents_returns_created_document():
    client = TestClient(create_app())
    client.post("/api/documents/import-url", json={"value": "https://example.com/paper.pdf"})

    response = client.get("/api/documents")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["source_type"] == "pdf_url"
