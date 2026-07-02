from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_settings_use_env_defaults(monkeypatch):
    monkeypatch.setenv("PAPER_READER_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("PAPER_READER_CHAT_MODEL", "demo-model")

    client = TestClient(create_app())

    response = client.get("/api/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["api_base_url"] == "https://example.test/v1"
    assert body["chat_model"] == "demo-model"
    assert body["api_key_configured"] is False


def test_settings_override_is_saved():
    client = TestClient(create_app())

    response = client.put(
        "/api/settings",
        json={
            "api_base_url": "https://api.local/v1",
            "api_key": "secret-key",
            "chat_model": "reader-model",
            "request_timeout_seconds": 30,
            "temperature": 0.1,
        },
    )

    assert response.status_code == 200

    response = client.get("/api/settings")
    body = response.json()
    assert body["api_base_url"] == "https://api.local/v1"
    assert body["chat_model"] == "reader-model"
    assert body["request_timeout_seconds"] == 30
    assert body["temperature"] == 0.1
    assert body["api_key_configured"] is True
    assert "api_key" not in body
