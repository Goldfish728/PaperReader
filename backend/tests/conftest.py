import os
from collections.abc import Iterator

import pytest

from backend.app.core.config import get_settings


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path) -> Iterator[None]:
    os.environ["PAPER_READER_DATA_DIR"] = str(tmp_path / "data")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
