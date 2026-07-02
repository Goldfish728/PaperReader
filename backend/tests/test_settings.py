from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.app.db.engine import get_engine, init_db
from backend.app.db.models import AppSetting
from backend.app.db.repositories import SettingsRepository
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


def test_blank_api_key_override_falls_back_to_env_key(monkeypatch):
    monkeypatch.setenv("PAPER_READER_API_KEY", "env-secret-key")

    client = TestClient(create_app())

    response = client.put(
        "/api/settings",
        json={
            "api_base_url": "https://api.local/v1",
            "api_key": "",
            "chat_model": "reader-model",
            "request_timeout_seconds": 30,
            "temperature": 0.1,
        },
    )

    assert response.status_code == 200

    response = client.get("/api/settings")
    body = response.json()
    assert body["api_key_configured"] is True
    assert "api_key" not in body


def test_setting_updated_at_changes_when_existing_value_changes():
    init_db()
    past_updated_at = datetime(2020, 1, 1, tzinfo=UTC)

    with Session(get_engine()) as session:
        repo = SettingsRepository(session)
        repo.set_value("chat_model", "old-model")
        session.commit()

        setting = session.get(AppSetting, "chat_model")
        assert setting is not None
        setting.updated_at = past_updated_at
        session.add(setting)
        session.commit()
        session.refresh(setting)
        stored_past_updated_at = setting.updated_at

        repo.set_value("chat_model", "new-model")
        session.commit()
        session.refresh(setting)

        assert setting.value == "new-model"
        assert setting.updated_at > stored_past_updated_at
