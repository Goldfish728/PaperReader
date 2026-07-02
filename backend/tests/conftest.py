from collections.abc import Iterator

import pytest

from backend.app.core.config import get_settings


@pytest.fixture(autouse=True)
def isolated_data_dir(monkeypatch, tmp_path) -> Iterator[None]:
    monkeypatch.setenv("PAPER_READER_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
