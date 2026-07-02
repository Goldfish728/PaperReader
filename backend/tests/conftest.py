from collections.abc import Iterator

import pytest

from backend.app.core.config import get_settings
from backend.app.db.engine import reset_engine


@pytest.fixture(autouse=True)
def isolated_data_dir(monkeypatch, tmp_path) -> Iterator[None]:
    monkeypatch.setenv("PAPER_READER_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_engine()
    yield
    get_settings.cache_clear()
    reset_engine()
