from backend.app.core.config import get_settings
from backend.app.db import engine as db_engine


def test_get_engine_is_cached_until_reset(monkeypatch, tmp_path):
    first_engine = db_engine.get_engine()

    assert db_engine.get_engine() is first_engine

    monkeypatch.setenv("PAPER_READER_DATA_DIR", str(tmp_path / "other-data"))
    get_settings.cache_clear()

    assert db_engine.get_engine() is first_engine

    db_engine.reset_engine()

    second_engine = db_engine.get_engine()
    assert second_engine is not first_engine
    assert str(second_engine.url) == f"sqlite:///{tmp_path / 'other-data' / 'app.db'}"
