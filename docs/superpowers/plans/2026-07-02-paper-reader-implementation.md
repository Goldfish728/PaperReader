# PaperReader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local FastAPI + React web app that imports PDFs, arXiv links, PDF URLs, and readable web articles, then generates Chinese structured-reading and deep-reading notes with current-document chat.

**Architecture:** The backend owns ingestion, parsing, persistence, note generation, FTS retrieval, and model calls. The frontend is a three-column workspace that talks to the backend over JSON APIs and polls document job status. SQLite stores app state and FTS indexes, while `data/documents/<document_id>/` stores source files, extracted images, and generated Markdown notes.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, SQLite FTS5, PyMuPDF, trafilatura, httpx, pytest, React, TypeScript, Vite, lucide-react.

---

## File Structure

Create this structure:

```text
PaperReader/
  README.md
  .env.example
  .gitignore
  pyproject.toml
  backend/
    app/
      __init__.py
      main.py
      api/
        __init__.py
        documents.py
        settings.py
      core/
        __init__.py
        config.py
        paths.py
      db/
        __init__.py
        engine.py
        fts.py
        models.py
        repositories.py
      services/
        __init__.py
        chat_engine.py
        chunker.py
        fetcher.py
        figure_extractor.py
        html_parser.py
        job_manager.py
        model_client.py
        note_generator.py
        pdf_parser.py
        source_detector.py
      schemas/
        __init__.py
        documents.py
        settings.py
    tests/
      conftest.py
      test_source_detector.py
      test_chunker_fts.py
      test_settings.py
      test_api_documents.py
  frontend/
    index.html
    package.json
    tsconfig.json
    vite.config.ts
    src/
      App.tsx
      main.tsx
      api/client.ts
      components/
        ChatPanel.tsx
        DocumentList.tsx
        ImportBox.tsx
        NoteViewer.tsx
        SettingsDialog.tsx
      styles.css
```

Responsibilities:

- `backend/app/main.py`: create FastAPI app, initialize database, include routers, expose document asset files.
- `backend/app/core/config.py`: resolve `.env` settings and runtime paths.
- `backend/app/core/paths.py`: create and resolve local `data/` paths safely.
- `backend/app/db/models.py`: SQLModel tables for documents, sections, chunks, figures, notes, messages, assets, and settings.
- `backend/app/db/fts.py`: create and query SQLite FTS5 tables for chunks.
- `backend/app/db/repositories.py`: persistence helpers with small, explicit methods.
- `backend/app/services/source_detector.py`: classify uploads, URLs, and arXiv IDs.
- `backend/app/services/fetcher.py`: save uploads, download PDFs, resolve arXiv metadata, save HTML snapshots.
- `backend/app/services/pdf_parser.py`: parse text-based PDFs into sections, pages, and metadata candidates.
- `backend/app/services/html_parser.py`: extract readable article text and metadata.
- `backend/app/services/figure_extractor.py`: extract PDF images and associate captions.
- `backend/app/services/chunker.py`: create section-aware chunks.
- `backend/app/services/model_client.py`: call OpenAI-compatible chat completions.
- `backend/app/services/note_generator.py`: generate `structured_reading_note.md` and `deep_reading_note.md`.
- `backend/app/services/chat_engine.py`: convert Chinese questions to search terms, retrieve chunks, and answer.
- `backend/app/services/job_manager.py`: orchestrate document processing status transitions.
- `backend/app/api/documents.py`: document import, status, notes, chat, delete, regenerate APIs.
- `backend/app/api/settings.py`: settings read/update APIs.
- `frontend/src/App.tsx`: app shell and selected-document state.
- `frontend/src/components/*`: focused UI pieces for import, list, note tabs, chat, and settings.

---

### Task 1: Backend Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/paths.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Add Python project metadata and dependencies**

Create `pyproject.toml`:

```toml
[project]
name = "paper-reader"
version = "0.1.0"
description = "Local English paper reader with Chinese notes and chat."
requires-python = ">=3.11"
dependencies = [
  "beautifulsoup4>=4.12.3",
  "fastapi>=0.115.0",
  "httpx>=0.27.0",
  "pydantic-settings>=2.4.0",
  "pymupdf>=1.24.9",
  "python-multipart>=0.0.9",
  "sqlmodel>=0.0.22",
  "trafilatura>=1.12.0",
  "uvicorn[standard]>=0.30.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.23.8",
  "ruff>=0.6.0"
]

[tool.pytest.ini_options]
testpaths = ["backend/tests"]
pythonpath = ["."]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 2: Add environment example**

Create `.env.example`:

```bash
PAPER_READER_DATA_DIR=./data
PAPER_READER_API_BASE_URL=https://api.openai.com/v1
PAPER_READER_API_KEY=
PAPER_READER_CHAT_MODEL=gpt-4.1-mini
PAPER_READER_REQUEST_TIMEOUT_SECONDS=120
PAPER_READER_TEMPERATURE=0.2
```

- [ ] **Step 3: Add concise README**

Create `README.md`:

```markdown
# PaperReader

PaperReader is a local web app for reading English papers and technical articles in Chinese.

First-version capabilities:

- Upload text-based PDF files.
- Import PDF URLs, arXiv links, arXiv IDs, and readable web article URLs.
- Generate two Chinese notes: `全文理解` and `整篇精读`.
- Ask questions about the current document.
- Store source files, generated notes, figures, and chat history locally.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn backend.app.main:app --reload
```

The frontend setup is added in a later task.
```

- [ ] **Step 4: Add backend app package files**

Create empty package markers:

```python
# backend/app/__init__.py
```

```python
# backend/app/core/__init__.py
```

- [ ] **Step 5: Add settings loader**

Create `backend/app/core/config.py`:

```python
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PAPER_READER_", env_file=".env")

    data_dir: Path = Field(default=Path("./data"))
    api_base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="")
    chat_model: str = Field(default="gpt-4.1-mini")
    request_timeout_seconds: int = Field(default=120)
    temperature: float = Field(default=0.2)


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
```

- [ ] **Step 6: Add local path helpers**

Create `backend/app/core/paths.py`:

```python
from pathlib import Path

from backend.app.core.config import get_settings


def data_dir() -> Path:
    root = get_settings().data_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def document_dir(document_id: str) -> Path:
    path = data_dir() / "documents" / document_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def figures_dir(document_id: str) -> Path:
    path = document_dir(document_id) / "figures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "app.db"
```

- [ ] **Step 7: Add FastAPI health endpoint**

Create `backend/app/main.py`:

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="PaperReader", version="0.1.0")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 8: Add pytest fixture for isolated data directory**

Create `backend/tests/conftest.py`:

```python
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
```

- [ ] **Step 9: Run skeleton verification**

Run:

```bash
python -m pip install -e ".[dev]"
pytest -q
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Expected:

```text
0 tests collected
Uvicorn running on http://127.0.0.1:8000
```

Stop the server with `Ctrl+C`.

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml README.md .env.example backend
git commit -m "chore: scaffold backend app"
```

---

### Task 2: Database Models and Settings Resolution

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/models.py`
- Create: `backend/app/db/engine.py`
- Create: `backend/app/db/repositories.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/settings.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/settings.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_settings.py`

- [ ] **Step 1: Write settings API tests**

Create `backend/tests/test_settings.py`:

```python
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
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_settings.py -q
```

Expected: fails because `/api/settings` is not registered.

- [ ] **Step 3: Add database models**

Create `backend/app/db/__init__.py`:

```python
# Database package for PaperReader.
```

Create `backend/app/db/models.py`:

```python
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


def new_id() -> str:
    return uuid4().hex


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(StrEnum):
    UPLOADED_PDF = "uploaded_pdf"
    PDF_URL = "pdf_url"
    ARXIV = "arxiv"
    HTML_ARTICLE = "html_article"


class DocumentStatus(StrEnum):
    QUEUED = "queued"
    FETCHING = "fetching"
    PARSING = "parsing"
    EXTRACTING_FIGURES = "extracting_figures"
    GENERATING_STRUCTURED_READING = "generating_structured_reading"
    GENERATING_DEEP_READING = "generating_deep_reading"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class NoteKind(StrEnum):
    STRUCTURED_READING = "structured_reading"
    DEEP_READING = "deep_reading"


class AssetKind(StrEnum):
    ORIGINAL_PDF = "original_pdf"
    SOURCE_HTML = "source_html"
    FIGURE = "figure"
    NOTE = "note"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class Document(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    title: str = Field(default="Untitled")
    authors_json: str = Field(default="[]")
    source_type: SourceType
    original_url: Optional[str] = None
    abstract: Optional[str] = None
    status: DocumentStatus = Field(default=DocumentStatus.QUEUED, index=True)
    error_message: Optional[str] = None
    model_snapshot_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DocumentAsset(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    kind: AssetKind
    path: str
    label: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class Section(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    number: Optional[str] = None
    title: str
    level: int = Field(default=1)
    parent_id: Optional[str] = None
    order: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    text: str = Field(default="")


class Chunk(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    section_id: Optional[str] = Field(default=None, index=True)
    section_label: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    order: int
    text: str


class Figure(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    section_id: Optional[str] = Field(default=None, index=True)
    label: Optional[str] = None
    caption: Optional[str] = None
    page: Optional[int] = None
    image_path: str
    order: int


class Note(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    kind: NoteKind
    markdown: str
    path: str
    created_at: datetime = Field(default_factory=utc_now)


class ChatMessage(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    document_id: str = Field(index=True)
    role: ChatRole
    content: str
    related_chunks_json: str = Field(default="[]")
    created_at: datetime = Field(default_factory=utc_now)


class AppSetting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str
    updated_at: datetime = Field(default_factory=utc_now)
```

- [ ] **Step 4: Add database engine and init**

Create `backend/app/db/engine.py`:

```python
from sqlmodel import Session, SQLModel, create_engine

from backend.app.core.paths import database_path


def get_engine():
    path = database_path()
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(get_engine())


def get_session():
    with Session(get_engine()) as session:
        yield session
```

- [ ] **Step 5: Add settings schemas**

Create `backend/app/schemas/__init__.py`:

```python
# API schema package for PaperReader.
```

Create `backend/app/schemas/settings.py`:

```python
from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    api_base_url: str = Field(min_length=1)
    api_key: str = Field(default="")
    chat_model: str = Field(min_length=1)
    request_timeout_seconds: int = Field(default=120, ge=5, le=600)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class SettingsRead(BaseModel):
    api_base_url: str
    chat_model: str
    request_timeout_seconds: int
    temperature: float
    api_key_configured: bool
```

- [ ] **Step 6: Add settings repository helpers**

Create `backend/app/db/repositories.py`:

```python
from sqlmodel import Session, select

from backend.app.db.models import AppSetting


class SettingsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_value(self, key: str) -> str | None:
        setting = self.session.get(AppSetting, key)
        return setting.value if setting else None

    def set_value(self, key: str, value: str) -> None:
        setting = self.session.get(AppSetting, key)
        if setting is None:
            setting = AppSetting(key=key, value=value)
            self.session.add(setting)
        else:
            setting.value = value
            self.session.add(setting)

    def list_all(self) -> dict[str, str]:
        rows = self.session.exec(select(AppSetting)).all()
        return {row.key: row.value for row in rows}
```

- [ ] **Step 7: Add settings API**

Create `backend/app/api/__init__.py`:

```python
# API routers for PaperReader.
```

Create `backend/app/api/settings.py`:

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.app.core.config import get_settings
from backend.app.db.engine import get_session
from backend.app.db.repositories import SettingsRepository
from backend.app.schemas.settings import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def resolved_settings(session: Session) -> SettingsRead:
    env = get_settings()
    repo = SettingsRepository(session)
    values = repo.list_all()
    api_key = values.get("api_key", env.api_key)
    return SettingsRead(
        api_base_url=values.get("api_base_url", env.api_base_url),
        chat_model=values.get("chat_model", env.chat_model),
        request_timeout_seconds=int(
            values.get("request_timeout_seconds", env.request_timeout_seconds)
        ),
        temperature=float(values.get("temperature", env.temperature)),
        api_key_configured=bool(api_key),
    )


@router.get("", response_model=SettingsRead)
def read_settings(session: Session = Depends(get_session)) -> SettingsRead:
    return resolved_settings(session)


@router.put("", response_model=SettingsRead)
def update_settings(
    payload: SettingsUpdate, session: Session = Depends(get_session)
) -> SettingsRead:
    repo = SettingsRepository(session)
    repo.set_value("api_base_url", payload.api_base_url)
    repo.set_value("api_key", payload.api_key)
    repo.set_value("chat_model", payload.chat_model)
    repo.set_value("request_timeout_seconds", str(payload.request_timeout_seconds))
    repo.set_value("temperature", str(payload.temperature))
    session.commit()
    return resolved_settings(session)
```

- [ ] **Step 8: Register API router and initialize database**

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI

from backend.app.api.settings import router as settings_router
from backend.app.db.engine import init_db


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="PaperReader", version="0.1.0")
    app.include_router(settings_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 9: Run tests**

Run:

```bash
pytest backend/tests/test_settings.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 10: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: add database settings"
```

---

### Task 3: Source Detection and Import API Shell

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/source_detector.py`
- Create: `backend/app/schemas/documents.py`
- Create: `backend/app/api/documents.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/db/repositories.py`
- Test: `backend/tests/test_source_detector.py`
- Test: `backend/tests/test_api_documents.py`

- [ ] **Step 1: Write source detector tests**

Create `backend/tests/test_source_detector.py`:

```python
from backend.app.db.models import SourceType
from backend.app.services.source_detector import detect_text_source, normalize_arxiv_id


def test_detect_arxiv_abs_url():
    detected = detect_text_source("https://arxiv.org/abs/2401.12345")

    assert detected.source_type == SourceType.ARXIV
    assert detected.normalized_value == "2401.12345"


def test_detect_arxiv_pdf_url():
    detected = detect_text_source("https://arxiv.org/pdf/2401.12345")

    assert detected.source_type == SourceType.ARXIV
    assert detected.normalized_value == "2401.12345"


def test_detect_plain_arxiv_id():
    detected = detect_text_source("2401.12345v2")

    assert detected.source_type == SourceType.ARXIV
    assert detected.normalized_value == "2401.12345v2"


def test_detect_pdf_url():
    detected = detect_text_source("https://example.com/paper.pdf")

    assert detected.source_type == SourceType.PDF_URL
    assert detected.normalized_value == "https://example.com/paper.pdf"


def test_detect_html_article_url():
    detected = detect_text_source("https://example.com/posts/paper-reader")

    assert detected.source_type == SourceType.HTML_ARTICLE


def test_normalize_old_style_arxiv_id():
    assert normalize_arxiv_id("cs/9901001") == "cs/9901001"
```

- [ ] **Step 2: Write import API tests**

Create `backend/tests/test_api_documents.py`:

```python
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
```

- [ ] **Step 3: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_source_detector.py backend/tests/test_api_documents.py -q
```

Expected: fails because source detector and document API are missing.

- [ ] **Step 4: Add source detector**

Create `backend/app/services/__init__.py`:

```python
# Service package for PaperReader.
```

Create `backend/app/services/source_detector.py`:

```python
import re
from dataclasses import dataclass

from backend.app.db.models import SourceType

ARXIV_NEW_STYLE_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
ARXIV_OLD_STYLE_RE = re.compile(r"^[a-z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$", re.IGNORECASE)


@dataclass(frozen=True)
class DetectedSource:
    source_type: SourceType
    normalized_value: str


def normalize_arxiv_id(value: str) -> str | None:
    stripped = value.strip()
    if stripped.startswith("http://") or stripped.startswith("https://"):
        match = re.search(r"arxiv\.org/(abs|pdf)/([^?#]+)", stripped)
        if not match:
            return None
        arxiv_id = match.group(2).removesuffix(".pdf")
        return arxiv_id
    if ARXIV_NEW_STYLE_RE.match(stripped) or ARXIV_OLD_STYLE_RE.match(stripped):
        return stripped
    return None


def detect_text_source(value: str) -> DetectedSource:
    stripped = value.strip()
    arxiv_id = normalize_arxiv_id(stripped)
    if arxiv_id:
        return DetectedSource(SourceType.ARXIV, arxiv_id)
    if stripped.lower().split("?")[0].endswith(".pdf"):
        return DetectedSource(SourceType.PDF_URL, stripped)
    return DetectedSource(SourceType.HTML_ARTICLE, stripped)
```

- [ ] **Step 5: Add document schemas**

Create `backend/app/schemas/documents.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.db.models import DocumentStatus, SourceType


class ImportUrlRequest(BaseModel):
    value: str = Field(min_length=1)


class DocumentRead(BaseModel):
    id: str
    title: str
    source_type: SourceType
    original_url: str | None
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 6: Add document repository helpers**

Append to `backend/app/db/repositories.py`:

```python
from datetime import datetime, timezone

from sqlmodel import select

from backend.app.db.models import Document, DocumentStatus, SourceType


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_document(
        self,
        *,
        title: str,
        source_type: SourceType,
        original_url: str | None = None,
    ) -> Document:
        document = Document(
            title=title,
            source_type=source_type,
            original_url=original_url,
            status=DocumentStatus.QUEUED,
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def list_documents(self) -> list[Document]:
        return list(
            self.session.exec(
                select(Document).order_by(Document.created_at.desc())
            ).all()
        )

    def update_status(
        self,
        document: Document,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> Document:
        document.status = status
        document.error_message = error_message
        document.updated_at = datetime.now(timezone.utc)
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document
```

- [ ] **Step 7: Add document API shell**

Create `backend/app/api/documents.py`:

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.app.db.engine import get_session
from backend.app.db.repositories import DocumentRepository
from backend.app.schemas.documents import DocumentRead, ImportUrlRequest
from backend.app.services.source_detector import detect_text_source

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(session: Session = Depends(get_session)):
    return DocumentRepository(session).list_documents()


@router.post("/import-url", response_model=DocumentRead)
def import_url(payload: ImportUrlRequest, session: Session = Depends(get_session)):
    detected = detect_text_source(payload.value)
    title = detected.normalized_value if detected.source_type.value == "arxiv" else payload.value
    document = DocumentRepository(session).create_document(
        title=title,
        source_type=detected.source_type,
        original_url=payload.value,
    )
    return document
```

- [ ] **Step 8: Register document router**

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI

from backend.app.api.documents import router as documents_router
from backend.app.api.settings import router as settings_router
from backend.app.db.engine import init_db


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="PaperReader", version="0.1.0")
    app.include_router(settings_router)
    app.include_router(documents_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 9: Run tests**

Run:

```bash
pytest backend/tests/test_source_detector.py backend/tests/test_api_documents.py backend/tests/test_settings.py -q
```

Expected:

```text
10 passed
```

- [ ] **Step 10: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: add document source detection"
```

---

### Task 4: Fetchers for Upload, PDF URL, arXiv, and HTML

**Files:**
- Create: `backend/app/services/fetcher.py`
- Modify: `backend/app/api/documents.py`
- Modify: `backend/app/db/repositories.py`
- Modify: `backend/app/schemas/documents.py`
- Test: `backend/tests/test_api_documents.py`

- [ ] **Step 1: Extend API tests for upload and fetch shell**

Append to `backend/tests/test_api_documents.py`:

```python
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
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_api_documents.py -q
```

Expected: upload tests fail because `/api/documents/upload` is missing.

- [ ] **Step 3: Add fetch result and upload saver**

Create `backend/app/services/fetcher.py`:

```python
from dataclasses import dataclass
from pathlib import Path

import httpx
from fastapi import UploadFile

from backend.app.core.paths import document_dir
from backend.app.db.models import SourceType


@dataclass(frozen=True)
class FetchResult:
    source_type: SourceType
    title: str
    original_path: Path
    original_url: str | None = None
    abstract: str | None = None
    authors: list[str] | None = None


async def save_uploaded_pdf(document_id: str, file: UploadFile) -> Path:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF uploads are supported in this version.")
    path = document_dir(document_id) / "original.pdf"
    content = await file.read()
    if not content.startswith(b"%PDF"):
        raise ValueError("Uploaded file does not look like a PDF.")
    path.write_bytes(content)
    return path


async def download_pdf(document_id: str, url: str, timeout_seconds: int = 60) -> Path:
    path = document_dir(document_id) / "original.pdf"
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    content = response.content
    content_type = response.headers.get("content-type", "").lower()
    if "pdf" not in content_type and not content.startswith(b"%PDF"):
        raise ValueError("URL did not return a PDF file.")
    path.write_bytes(content)
    return path


async def download_html(document_id: str, url: str, timeout_seconds: int = 60) -> Path:
    path = document_dir(document_id) / "source.html"
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    path.write_text(response.text, encoding=response.encoding or "utf-8")
    return path
```

- [ ] **Step 4: Add document asset repository**

Append to `backend/app/db/repositories.py`:

```python
from backend.app.db.models import AssetKind, DocumentAsset


class AssetRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_asset(
        self,
        *,
        document_id: str,
        kind: AssetKind,
        path: str,
        label: str | None = None,
    ) -> DocumentAsset:
        asset = DocumentAsset(
            document_id=document_id,
            kind=kind,
            path=path,
            label=label,
        )
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset
```

- [ ] **Step 5: Add upload endpoint**

Modify `backend/app/api/documents.py`:

```python
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from backend.app.db.engine import get_session
from backend.app.db.models import AssetKind, SourceType
from backend.app.db.repositories import AssetRepository, DocumentRepository
from backend.app.schemas.documents import DocumentRead, ImportUrlRequest
from backend.app.services.fetcher import save_uploaded_pdf
from backend.app.services.source_detector import detect_text_source

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(session: Session = Depends(get_session)):
    return DocumentRepository(session).list_documents()


@router.post("/import-url", response_model=DocumentRead)
def import_url(payload: ImportUrlRequest, session: Session = Depends(get_session)):
    detected = detect_text_source(payload.value)
    title = detected.normalized_value if detected.source_type == SourceType.ARXIV else payload.value
    document = DocumentRepository(session).create_document(
        title=title,
        source_type=detected.source_type,
        original_url=payload.value,
    )
    return document


@router.post("/upload", response_model=DocumentRead)
async def upload_pdf(
    file: UploadFile = File(...), session: Session = Depends(get_session)
):
    document = DocumentRepository(session).create_document(
        title=file.filename or "uploaded.pdf",
        source_type=SourceType.UPLOADED_PDF,
        original_url=None,
    )
    try:
        path = await save_uploaded_pdf(document.id, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    AssetRepository(session).create_asset(
        document_id=document.id,
        kind=AssetKind.ORIGINAL_PDF,
        path=str(path),
        label="Original PDF",
    )
    return document
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest backend/tests/test_api_documents.py backend/tests/test_source_detector.py -q
```

Expected:

```text
8 passed
```

- [ ] **Step 7: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: add document import shell"
```

---

### Task 5: PDF and HTML Parsing

**Files:**
- Create: `backend/app/services/pdf_parser.py`
- Create: `backend/app/services/html_parser.py`
- Modify: `backend/app/db/repositories.py`
- Test: `backend/tests/test_pdf_parser.py`
- Test: `backend/tests/test_html_parser.py`

- [ ] **Step 1: Write parser tests**

Create `backend/tests/test_html_parser.py`:

```python
from pathlib import Path

from backend.app.services.html_parser import parse_html_article


def test_parse_html_article_extracts_title_and_text(tmp_path: Path):
    html_path = tmp_path / "source.html"
    html_path.write_text(
        """
        <html>
          <head><title>Readable Article</title></head>
          <body>
            <article>
              <h1>Readable Article</h1>
              <p>This article explains a method for paper reading.</p>
              <p>The method has three stages and a final evaluation.</p>
            </article>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    parsed = parse_html_article(html_path)

    assert parsed.title == "Readable Article"
    assert "paper reading" in parsed.raw_text
    assert len(parsed.sections) == 1
    assert parsed.sections[0].title == "Readable Article"
```

Create `backend/tests/test_pdf_parser.py`:

```python
from backend.app.services.pdf_parser import detect_heading_level


def test_detect_numbered_heading_level():
    assert detect_heading_level("1 Introduction") == 1
    assert detect_heading_level("2.3 Training Objective") == 2
    assert detect_heading_level("A.1 Extra Results") == 2


def test_ignore_sentence_as_heading():
    assert detect_heading_level("This is a normal sentence with several words.") is None
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_html_parser.py backend/tests/test_pdf_parser.py -q
```

Expected: fails because parser modules are missing.

- [ ] **Step 3: Add parser data structures and PDF heading detection**

Create `backend/app/services/pdf_parser.py`:

```python
import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz


@dataclass
class ParsedSection:
    number: str | None
    title: str
    level: int
    order: int
    page_start: int | None
    page_end: int | None
    text: str


@dataclass
class ParsedDocument:
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str | None = None
    raw_text: str = ""
    sections: list[ParsedSection] = field(default_factory=list)


NUMBERED_HEADING_RE = re.compile(r"^((\d+)(\.\d+)*|[A-Z](\.\d+)*)\s+(.{3,120})$")


def detect_heading_level(line: str) -> int | None:
    stripped = " ".join(line.strip().split())
    if stripped.endswith(".") and len(stripped.split()) > 6:
        return None
    match = NUMBERED_HEADING_RE.match(stripped)
    if not match:
        return None
    number = match.group(1)
    if "." not in number:
        return 1
    return number.count(".") + 1


def parse_pdf(path: Path) -> ParsedDocument:
    doc = fitz.open(path)
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(doc, start=1):
        text = page.get_text("text")
        pages.append((index, text))
    raw_text = "\n".join(text for _, text in pages).strip()
    if not raw_text:
        raise ValueError("PDF has no extractable text.")

    first_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    title = first_lines[0][:200] if first_lines else path.stem
    sections = build_sections_from_pages(pages)
    return ParsedDocument(title=title, raw_text=raw_text, sections=sections)


def build_sections_from_pages(pages: list[tuple[int, str]]) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    current_title = "S1 Full Text"
    current_number = "S1"
    current_level = 1
    current_page_start = pages[0][0] if pages else None
    current_lines: list[str] = []

    def flush(page_end: int | None) -> None:
        if not current_lines:
            return
        sections.append(
            ParsedSection(
                number=current_number,
                title=current_title,
                level=current_level,
                order=len(sections),
                page_start=current_page_start,
                page_end=page_end,
                text="\n".join(current_lines).strip(),
            )
        )

    for page_number, page_text in pages:
        for line in page_text.splitlines():
            level = detect_heading_level(line)
            if level is not None and current_lines:
                flush(page_number)
                stripped = " ".join(line.strip().split())
                number, title = stripped.split(" ", 1)
                current_number = number
                current_title = stripped
                current_level = level
                current_page_start = page_number
                current_lines = [line]
            else:
                current_lines.append(line)
    flush(pages[-1][0] if pages else None)
    return sections
```

- [ ] **Step 4: Add HTML parser**

Create `backend/app/services/html_parser.py`:

```python
from pathlib import Path

from bs4 import BeautifulSoup
import trafilatura

from backend.app.services.pdf_parser import ParsedDocument, ParsedSection


def parse_html_article(path: Path) -> ParsedDocument:
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup, path)
    extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
    if not extracted:
        article = soup.find("article") or soup.body
        extracted = article.get_text("\n", strip=True) if article else ""
    raw_text = extracted.strip()
    if not raw_text:
        raise ValueError("Web page has no readable article text.")
    section = ParsedSection(
        number="S1",
        title=title,
        level=1,
        order=0,
        page_start=None,
        page_end=None,
        text=raw_text,
    )
    return ParsedDocument(title=title, raw_text=raw_text, sections=[section])


def extract_title(soup: BeautifulSoup, path: Path) -> str:
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)
    return path.stem
```

- [ ] **Step 5: Add repository helpers for parsed sections**

Append to `backend/app/db/repositories.py`:

```python
from backend.app.db.models import Section


class SectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_sections(self, document_id: str, parsed_sections) -> list[Section]:
        existing = self.session.exec(
            select(Section).where(Section.document_id == document_id)
        ).all()
        for row in existing:
            self.session.delete(row)
        created: list[Section] = []
        for parsed in parsed_sections:
            section = Section(
                document_id=document_id,
                number=parsed.number,
                title=parsed.title,
                level=parsed.level,
                order=parsed.order,
                page_start=parsed.page_start,
                page_end=parsed.page_end,
                text=parsed.text,
            )
            self.session.add(section)
            created.append(section)
        self.session.commit()
        return created
```

- [ ] **Step 6: Run parser tests**

Run:

```bash
pytest backend/tests/test_html_parser.py backend/tests/test_pdf_parser.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services backend/app/db/repositories.py backend/tests
git commit -m "feat: parse pdf and html sources"
```

---

### Task 6: Figure Extraction and Note Image Assets

**Files:**
- Create: `backend/app/services/figure_extractor.py`
- Modify: `backend/app/db/repositories.py`
- Test: `backend/tests/test_figure_extractor.py`

- [ ] **Step 1: Write caption matching tests**

Create `backend/tests/test_figure_extractor.py`:

```python
from backend.app.services.figure_extractor import find_captions


def test_find_figure_and_table_captions():
    text = """
    Figure 1: Overview of the proposed framework.
    Normal paragraph text.
    Table 2. Results on the benchmark datasets.
    Fig. 3 shows the ablation study.
    """

    captions = find_captions(text)

    assert captions == [
        "Figure 1: Overview of the proposed framework.",
        "Table 2. Results on the benchmark datasets.",
        "Fig. 3 shows the ablation study.",
    ]
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_figure_extractor.py -q
```

Expected: fails because figure extractor is missing.

- [ ] **Step 3: Add figure extraction service**

Create `backend/app/services/figure_extractor.py`:

```python
import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from backend.app.core.paths import figures_dir

CAPTION_RE = re.compile(r"^\s*((Figure|Fig\.|Table)\s+\d+[:.\s].{5,})$", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractedFigure:
    image_path: Path
    caption: str | None
    page: int
    order: int
    label: str | None


def find_captions(page_text: str) -> list[str]:
    captions: list[str] = []
    for line in page_text.splitlines():
        match = CAPTION_RE.match(line.strip())
        if match:
            captions.append(" ".join(match.group(1).split()))
    return captions


def extract_pdf_figures(document_id: str, pdf_path: Path) -> list[ExtractedFigure]:
    doc = fitz.open(pdf_path)
    output_dir = figures_dir(document_id)
    extracted: list[ExtractedFigure] = []
    for page_index, page in enumerate(doc, start=1):
        captions = find_captions(page.get_text("text"))
        images = page.get_images(full=True)
        for image_index, image in enumerate(images, start=1):
            xref = image[0]
            data = doc.extract_image(xref)
            extension = data.get("ext", "png")
            image_path = output_dir / f"page-{page_index:03d}-image-{image_index:02d}.{extension}"
            image_path.write_bytes(data["image"])
            caption = captions[min(image_index - 1, len(captions) - 1)] if captions else None
            label = caption.split(":", 1)[0] if caption and ":" in caption else None
            extracted.append(
                ExtractedFigure(
                    image_path=image_path,
                    caption=caption,
                    page=page_index,
                    order=len(extracted),
                    label=label,
                )
            )
    return extracted
```

- [ ] **Step 4: Add figure repository helper**

Append to `backend/app/db/repositories.py`:

```python
from backend.app.db.models import Figure


class FigureRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_figures(self, document_id: str, extracted_figures) -> list[Figure]:
        existing = self.session.exec(
            select(Figure).where(Figure.document_id == document_id)
        ).all()
        for row in existing:
            self.session.delete(row)
        created: list[Figure] = []
        for item in extracted_figures:
            figure = Figure(
                document_id=document_id,
                label=item.label,
                caption=item.caption,
                page=item.page,
                image_path=str(item.image_path),
                order=item.order,
            )
            self.session.add(figure)
            created.append(figure)
        self.session.commit()
        return created
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest backend/tests/test_figure_extractor.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/figure_extractor.py backend/app/db/repositories.py backend/tests/test_figure_extractor.py
git commit -m "feat: extract pdf figure assets"
```

---

### Task 7: Chunking and SQLite FTS5 Retrieval

**Files:**
- Create: `backend/app/services/chunker.py`
- Create: `backend/app/db/fts.py`
- Modify: `backend/app/db/engine.py`
- Modify: `backend/app/db/repositories.py`
- Test: `backend/tests/test_chunker_fts.py`

- [ ] **Step 1: Write chunking and FTS tests**

Create `backend/tests/test_chunker_fts.py`:

```python
from sqlmodel import Session

from backend.app.db.engine import get_engine, init_db
from backend.app.db.fts import rebuild_document_fts, search_document_chunks
from backend.app.db.models import Chunk, Document, SourceType
from backend.app.services.chunker import chunk_section_text


def test_chunk_section_text_preserves_section_label():
    chunks = chunk_section_text(
        document_id="doc1",
        section_id="sec1",
        section_label="3.2 Training",
        text="Sentence one. Sentence two. Sentence three.",
        page_start=5,
        page_end=6,
        max_chars=25,
    )

    assert len(chunks) >= 2
    assert all(chunk.section_label == "3.2 Training" for chunk in chunks)


def test_fts_search_returns_relevant_chunk():
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        document = Document(title="Demo", source_type=SourceType.UPLOADED_PDF)
        session.add(document)
        session.commit()
        session.refresh(document)
        chunk = Chunk(
            document_id=document.id,
            section_label="2 Method",
            order=0,
            text="The proposed method improves baseline accuracy with ablation evidence.",
        )
        session.add(chunk)
        session.commit()
        session.refresh(chunk)

        rebuild_document_fts(session, document.id)
        results = search_document_chunks(session, document.id, "baseline ablation")

    assert len(results) == 1
    assert results[0].chunk_id == chunk.id
    assert "baseline accuracy" in results[0].text
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_chunker_fts.py -q
```

Expected: fails because chunker and FTS modules are missing.

- [ ] **Step 3: Add chunker**

Create `backend/app/services/chunker.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkDraft:
    document_id: str
    section_id: str | None
    section_label: str | None
    page_start: int | None
    page_end: int | None
    order: int
    text: str


def chunk_section_text(
    *,
    document_id: str,
    section_id: str | None,
    section_label: str | None,
    text: str,
    page_start: int | None,
    page_end: int | None,
    max_chars: int = 1800,
) -> list[ChunkDraft]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[ChunkDraft] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return
        chunks.append(
            ChunkDraft(
                document_id=document_id,
                section_id=section_id,
                section_label=section_label,
                page_start=page_start,
                page_end=page_end,
                order=len(chunks),
                text="\n\n".join(current),
            )
        )
        current = []
        current_len = 0

    for paragraph in paragraphs:
        if current and current_len + len(paragraph) > max_chars:
            flush()
        current.append(paragraph)
        current_len += len(paragraph)
    flush()
    return chunks
```

- [ ] **Step 4: Add FTS table creation and search**

Create `backend/app/db/fts.py`:

```python
from dataclasses import dataclass

from sqlmodel import Session, text


@dataclass(frozen=True)
class FtsSearchResult:
    chunk_id: str
    section_label: str | None
    page_start: int | None
    page_end: int | None
    text: str
    rank: float


def init_fts(session: Session) -> None:
    session.exec(
        text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(chunk_id UNINDEXED, document_id UNINDEXED, section_label, text)
            """
        )
    )
    session.commit()


def rebuild_document_fts(session: Session, document_id: str) -> None:
    init_fts(session)
    session.exec(text("DELETE FROM chunks_fts WHERE document_id = :document_id"), {"document_id": document_id})
    rows = session.exec(
        text(
            """
            SELECT id, document_id, section_label, text
            FROM chunk
            WHERE document_id = :document_id
            ORDER BY "order"
            """
        ),
        {"document_id": document_id},
    ).all()
    for row in rows:
        session.exec(
            text(
                """
                INSERT INTO chunks_fts(chunk_id, document_id, section_label, text)
                VALUES (:chunk_id, :document_id, :section_label, :text)
                """
            ),
            {
                "chunk_id": row.id,
                "document_id": row.document_id,
                "section_label": row.section_label or "",
                "text": row.text,
            },
        )
    session.commit()


def search_document_chunks(
    session: Session,
    document_id: str,
    query: str,
    limit: int = 8,
) -> list[FtsSearchResult]:
    init_fts(session)
    safe_query = " ".join(token for token in query.replace('"', " ").split() if token)
    if not safe_query:
        return []
    rows = session.exec(
        text(
            """
            SELECT
              c.id AS chunk_id,
              c.section_label AS section_label,
              c.page_start AS page_start,
              c.page_end AS page_end,
              c.text AS text,
              bm25(chunks_fts) AS rank
            FROM chunks_fts
            JOIN chunk c ON c.id = chunks_fts.chunk_id
            WHERE chunks_fts MATCH :query
              AND chunks_fts.document_id = :document_id
            ORDER BY rank
            LIMIT :limit
            """
        ),
        {"query": safe_query, "document_id": document_id, "limit": limit},
    ).all()
    return [
        FtsSearchResult(
            chunk_id=row.chunk_id,
            section_label=row.section_label,
            page_start=row.page_start,
            page_end=row.page_end,
            text=row.text,
            rank=row.rank,
        )
        for row in rows
    ]
```

- [ ] **Step 5: Initialize FTS in database startup**

Modify `backend/app/db/engine.py`:

```python
from sqlmodel import Session, SQLModel, create_engine

from backend.app.core.paths import database_path


def get_engine():
    path = database_path()
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        from backend.app.db.fts import init_fts

        init_fts(session)


def get_session():
    with Session(get_engine()) as session:
        yield session
```

- [ ] **Step 6: Add chunk repository helper**

Append to `backend/app/db/repositories.py`:

```python
from backend.app.db.models import Chunk


class ChunkRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_chunks(self, document_id: str, chunk_drafts) -> list[Chunk]:
        existing = self.session.exec(
            select(Chunk).where(Chunk.document_id == document_id)
        ).all()
        for row in existing:
            self.session.delete(row)
        created: list[Chunk] = []
        for draft in chunk_drafts:
            chunk = Chunk(
                document_id=draft.document_id,
                section_id=draft.section_id,
                section_label=draft.section_label,
                page_start=draft.page_start,
                page_end=draft.page_end,
                order=draft.order,
                text=draft.text,
            )
            self.session.add(chunk)
            created.append(chunk)
        self.session.commit()
        return created
```

- [ ] **Step 7: Run tests**

Run:

```bash
pytest backend/tests/test_chunker_fts.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 8: Commit**

```bash
git add backend/app backend/tests/test_chunker_fts.py
git commit -m "feat: add document full text search"
```

---

### Task 8: OpenAI-Compatible Model Client

**Files:**
- Create: `backend/app/services/model_client.py`
- Test: `backend/tests/test_model_client.py`

- [ ] **Step 1: Write model client request test**

Create `backend/tests/test_model_client.py`:

```python
import httpx
import pytest

from backend.app.services.model_client import ChatMessage, ModelClient


@pytest.mark.asyncio
async def test_model_client_posts_chat_completion():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["authorization"]
        captured["json"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "中文回答"}}
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = ModelClient(
        base_url="https://api.example.test/v1",
        api_key="key-123",
        model="demo-model",
        timeout_seconds=30,
        temperature=0.2,
        transport=transport,
    )

    result = await client.complete(
        messages=[ChatMessage(role="user", content="hello")]
    )

    assert result == "中文回答"
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["auth"] == "Bearer key-123"
    assert '"model":"demo-model"' in captured["json"].replace(" ", "")
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_model_client.py -q
```

Expected: fails because model client is missing.

- [ ] **Step 3: Add model client**

Create `backend/app/services/model_client.py`:

```python
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class ModelClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int,
        temperature: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.transport = transport

    async def complete(self, messages: list[ChatMessage]) -> str:
        if not self.api_key:
            raise ValueError("Model API key is not configured.")
        payload = {
            "model": self.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "temperature": self.temperature,
        }
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Model response did not contain assistant content.") from exc
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest backend/tests/test_model_client.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/model_client.py backend/tests/test_model_client.py
git commit -m "feat: add model client"
```

---

### Task 9: Note Generation Service

**Files:**
- Create: `backend/app/services/note_generator.py`
- Modify: `backend/app/db/repositories.py`
- Test: `backend/tests/test_note_generator.py`

- [ ] **Step 1: Write note generator tests with fake model**

Create `backend/tests/test_note_generator.py`:

```python
from pathlib import Path

import pytest

from backend.app.services.model_client import ChatMessage
from backend.app.services.note_generator import generate_notes
from backend.app.services.pdf_parser import ParsedDocument, ParsedSection


class FakeModelClient:
    async def complete(self, messages: list[ChatMessage]) -> str:
        joined = "\n".join(message.content for message in messages)
        if "结构化全文理解" in joined:
            return "# 全文理解\n\n## 1 Introduction\n\n中文结构化说明。"
        return "# 整篇精读\n\n## 核心贡献\n\n中文精读说明。"


@pytest.mark.asyncio
async def test_generate_notes_writes_two_markdown_files(tmp_path: Path):
    parsed = ParsedDocument(
        title="Demo Paper",
        raw_text="1 Introduction\nThis paper introduces a method.",
        sections=[
            ParsedSection(
                number="1",
                title="1 Introduction",
                level=1,
                order=0,
                page_start=1,
                page_end=1,
                text="This paper introduces a method.",
            )
        ],
    )

    result = await generate_notes(
        document_id="doc1",
        parsed=parsed,
        figures=[],
        output_dir=tmp_path,
        model_client=FakeModelClient(),
    )

    assert result.structured_path.exists()
    assert result.deep_path.exists()
    assert "全文理解" in result.structured_markdown
    assert "整篇精读" in result.deep_markdown
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_note_generator.py -q
```

Expected: fails because note generator is missing.

- [ ] **Step 3: Add note generator**

Create `backend/app/services/note_generator.py`:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from backend.app.services.model_client import ChatMessage
from backend.app.services.pdf_parser import ParsedDocument


class CompletesChat(Protocol):
    async def complete(self, messages: list[ChatMessage]) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class GeneratedNotes:
    structured_markdown: str
    deep_markdown: str
    structured_path: Path
    deep_path: Path


def section_digest(parsed: ParsedDocument, max_chars_per_section: int = 3000) -> str:
    blocks: list[str] = []
    for section in parsed.sections:
        label = section.title
        text = section.text[:max_chars_per_section]
        blocks.append(f"## {label}\n{text}")
    return "\n\n".join(blocks)


async def generate_notes(
    *,
    document_id: str,
    parsed: ParsedDocument,
    figures: list,
    output_dir: Path,
    model_client: CompletesChat,
) -> GeneratedNotes:
    output_dir.mkdir(parents=True, exist_ok=True)
    digest = section_digest(parsed)
    figure_text = "\n".join(
        f"- {getattr(figure, 'label', '')}: {getattr(figure, 'caption', '')}"
        for figure in figures[:12]
    )
    structured = await model_client.complete(
        [
            ChatMessage(
                role="system",
                content=(
                    "你是英文论文中文精读助手。请生成结构化全文理解，保留原文标题层级、"
                    "章节编号、列表层级、图表和公式引用。不要逐句全文翻译。"
                ),
            ),
            ChatMessage(
                role="user",
                content=(
                    f"文档标题：{parsed.title}\n\n"
                    f"任务：生成结构化全文理解。\n\n"
                    f"章节内容：\n{digest}\n\n"
                    f"图表信息：\n{figure_text}"
                ),
            ),
        ]
    )
    deep = await model_client.complete(
        [
            ChatMessage(
                role="system",
                content=(
                    "你是资深研究论文导读助手。请生成整篇精读，解释问题、贡献、方法、"
                    "实验、关键图表、局限和读完应掌握的要点。"
                ),
            ),
            ChatMessage(
                role="user",
                content=(
                    f"文档标题：{parsed.title}\n\n"
                    f"结构化全文理解：\n{structured}\n\n"
                    f"原文章节摘要材料：\n{digest}\n\n"
                    f"图表信息：\n{figure_text}"
                ),
            ),
        ]
    )
    structured_path = output_dir / "structured_reading_note.md"
    deep_path = output_dir / "deep_reading_note.md"
    structured_path.write_text(structured, encoding="utf-8")
    deep_path.write_text(deep, encoding="utf-8")
    return GeneratedNotes(
        structured_markdown=structured,
        deep_markdown=deep,
        structured_path=structured_path,
        deep_path=deep_path,
    )
```

- [ ] **Step 4: Add note repository helper**

Append to `backend/app/db/repositories.py`:

```python
from backend.app.db.models import Note, NoteKind


class NoteRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_note(
        self,
        *,
        document_id: str,
        kind: NoteKind,
        markdown: str,
        path: str,
    ) -> Note:
        existing = self.session.exec(
            select(Note).where(Note.document_id == document_id, Note.kind == kind)
        ).all()
        for row in existing:
            self.session.delete(row)
        note = Note(document_id=document_id, kind=kind, markdown=markdown, path=path)
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def get_note(self, document_id: str, kind: NoteKind) -> Note | None:
        return self.session.exec(
            select(Note).where(Note.document_id == document_id, Note.kind == kind)
        ).first()
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest backend/tests/test_note_generator.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/note_generator.py backend/app/db/repositories.py backend/tests/test_note_generator.py
git commit -m "feat: generate reading notes"
```

---

### Task 10: Job Manager Pipeline

**Files:**
- Create: `backend/app/services/job_manager.py`
- Modify: `backend/app/api/documents.py`
- Modify: `backend/app/schemas/documents.py`
- Modify: `backend/app/db/repositories.py`
- Test: `backend/tests/test_job_manager.py`
- Test: `backend/tests/test_api_documents.py`

- [ ] **Step 1: Write job manager status test**

Create `backend/tests/test_job_manager.py`:

```python
from sqlmodel import Session

from backend.app.db.engine import get_engine, init_db
from backend.app.db.models import Document, DocumentStatus, SourceType
from backend.app.services.job_manager import mark_failed


def test_mark_failed_records_error_message():
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        document = Document(title="Demo", source_type=SourceType.UPLOADED_PDF)
        session.add(document)
        session.commit()
        session.refresh(document)

        mark_failed(session, document, "PDF has no extractable text.")

        session.refresh(document)
        assert document.status == DocumentStatus.FAILED
        assert document.error_message == "PDF has no extractable text."
```

- [ ] **Step 2: Extend document API tests for detail and notes**

Append to `backend/tests/test_api_documents.py`:

```python
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
```

- [ ] **Step 3: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_job_manager.py backend/tests/test_api_documents.py -q
```

Expected: fails because job manager and detail APIs are missing.

- [ ] **Step 4: Add job manager core**

Create `backend/app/services/job_manager.py`:

```python
from sqlmodel import Session

from backend.app.db.models import Document, DocumentStatus
from backend.app.db.repositories import DocumentRepository


def mark_failed(session: Session, document: Document, message: str) -> None:
    DocumentRepository(session).update_status(
        document,
        DocumentStatus.FAILED,
        error_message=message,
    )


def set_status(session: Session, document: Document, status: DocumentStatus) -> None:
    DocumentRepository(session).update_status(document, status, error_message=None)
```

- [ ] **Step 5: Extend document repository**

Append to `backend/app/db/repositories.py`:

```python
    def get_document(self, document_id: str) -> Document | None:
        return self.session.get(Document, document_id)
```

Place this method inside the existing `DocumentRepository` class. If it was appended outside the class during editing, move it directly under `list_documents`.

- [ ] **Step 6: Add note response schema**

Modify `backend/app/schemas/documents.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.db.models import DocumentStatus, NoteKind, SourceType


class ImportUrlRequest(BaseModel):
    value: str = Field(min_length=1)


class DocumentRead(BaseModel):
    id: str
    title: str
    source_type: SourceType
    original_url: str | None
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class NoteRead(BaseModel):
    document_id: str
    kind: NoteKind
    markdown: str
```

- [ ] **Step 7: Add detail and note endpoints**

Modify `backend/app/api/documents.py`:

```python
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from backend.app.db.engine import get_session
from backend.app.db.models import AssetKind, NoteKind, SourceType
from backend.app.db.repositories import AssetRepository, DocumentRepository, NoteRepository
from backend.app.schemas.documents import DocumentRead, ImportUrlRequest, NoteRead
from backend.app.services.fetcher import save_uploaded_pdf
from backend.app.services.source_detector import detect_text_source

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(session: Session = Depends(get_session)):
    return DocumentRepository(session).list_documents()


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, session: Session = Depends(get_session)):
    document = DocumentRepository(session).get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.get("/{document_id}/notes/{kind}", response_model=NoteRead)
def get_note(
    document_id: str,
    kind: NoteKind,
    session: Session = Depends(get_session),
):
    note = NoteRepository(session).get_note(document_id, kind)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    return NoteRead(document_id=document_id, kind=kind, markdown=note.markdown)


@router.post("/import-url", response_model=DocumentRead)
def import_url(payload: ImportUrlRequest, session: Session = Depends(get_session)):
    detected = detect_text_source(payload.value)
    title = detected.normalized_value if detected.source_type == SourceType.ARXIV else payload.value
    document = DocumentRepository(session).create_document(
        title=title,
        source_type=detected.source_type,
        original_url=payload.value,
    )
    return document


@router.post("/upload", response_model=DocumentRead)
async def upload_pdf(
    file: UploadFile = File(...), session: Session = Depends(get_session)
):
    document = DocumentRepository(session).create_document(
        title=file.filename or "uploaded.pdf",
        source_type=SourceType.UPLOADED_PDF,
        original_url=None,
    )
    try:
        path = await save_uploaded_pdf(document.id, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    AssetRepository(session).create_asset(
        document_id=document.id,
        kind=AssetKind.ORIGINAL_PDF,
        path=str(path),
        label="Original PDF",
    )
    return document
```

- [ ] **Step 8: Run tests**

Run:

```bash
pytest backend/tests/test_job_manager.py backend/tests/test_api_documents.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 9: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: add document job state APIs"
```

---

### Task 11: Chat Engine with FTS Grounding

**Files:**
- Create: `backend/app/services/chat_engine.py`
- Modify: `backend/app/schemas/documents.py`
- Modify: `backend/app/api/documents.py`
- Modify: `backend/app/db/repositories.py`
- Test: `backend/tests/test_chat_engine.py`

- [ ] **Step 1: Write chat engine test**

Create `backend/tests/test_chat_engine.py`:

```python
import pytest
from sqlmodel import Session

from backend.app.db.engine import get_engine, init_db
from backend.app.db.fts import rebuild_document_fts
from backend.app.db.models import Chunk, Document, SourceType
from backend.app.services.chat_engine import answer_question
from backend.app.services.model_client import ChatMessage


class FakeModelClient:
    async def complete(self, messages: list[ChatMessage]) -> str:
        joined = "\n".join(message.content for message in messages)
        assert "baseline accuracy" in joined
        return "这个方法通过消融实验说明相比 baseline 有提升。"


@pytest.mark.asyncio
async def test_answer_question_uses_retrieved_chunks():
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        document = Document(title="Demo", source_type=SourceType.UPLOADED_PDF)
        session.add(document)
        session.commit()
        session.refresh(document)
        chunk = Chunk(
            document_id=document.id,
            section_label="4 Experiments",
            order=0,
            text="The method improves baseline accuracy in the ablation study.",
        )
        session.add(chunk)
        session.commit()
        rebuild_document_fts(session, document.id)

        result = await answer_question(
            session=session,
            document_id=document.id,
            question="这个方法相比 baseline 有什么提升？",
            model_client=FakeModelClient(),
        )

    assert "消融实验" in result.answer
    assert result.related_chunks[0].section_label == "4 Experiments"
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_chat_engine.py -q
```

Expected: fails because chat engine is missing.

- [ ] **Step 3: Add chat engine**

Create `backend/app/services/chat_engine.py`:

```python
from dataclasses import dataclass
from typing import Protocol

from sqlmodel import Session

from backend.app.db.fts import FtsSearchResult, search_document_chunks
from backend.app.services.model_client import ChatMessage


class CompletesChat(Protocol):
    async def complete(self, messages: list[ChatMessage]) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class ChatAnswer:
    answer: str
    related_chunks: list[FtsSearchResult]


def search_terms_from_question(question: str) -> str:
    manual_map = {
        "基线": "baseline",
        "对比": "comparison",
        "提升": "improvement accuracy performance",
        "消融": "ablation",
        "实验": "experiment results",
        "方法": "method approach",
        "贡献": "contribution",
        "局限": "limitation",
    }
    terms = [question]
    for chinese, english in manual_map.items():
        if chinese in question:
            terms.append(english)
    return " ".join(terms)


async def answer_question(
    *,
    session: Session,
    document_id: str,
    question: str,
    model_client: CompletesChat,
) -> ChatAnswer:
    query = search_terms_from_question(question)
    chunks = search_document_chunks(session, document_id, query, limit=8)
    context = "\n\n".join(
        f"[{index + 1}] {chunk.section_label or 'Unknown section'}"
        f"{' p.' + str(chunk.page_start) if chunk.page_start else ''}\n{chunk.text}"
        for index, chunk in enumerate(chunks)
    )
    answer = await model_client.complete(
        [
            ChatMessage(
                role="system",
                content=(
                    "你是论文阅读助手。请基于提供的原文片段用自然中文回答。"
                    "如果片段不足以回答，请说明缺少哪些信息。"
                ),
            ),
            ChatMessage(
                role="user",
                content=f"问题：{question}\n\n相关原文片段：\n{context}",
            ),
        ]
    )
    return ChatAnswer(answer=answer, related_chunks=chunks)
```

- [ ] **Step 4: Add chat schemas**

Modify `backend/app/schemas/documents.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.db.models import ChatRole, DocumentStatus, NoteKind, SourceType


class ImportUrlRequest(BaseModel):
    value: str = Field(min_length=1)


class DocumentRead(BaseModel):
    id: str
    title: str
    source_type: SourceType
    original_url: str | None
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class NoteRead(BaseModel):
    document_id: str
    kind: NoteKind
    markdown: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class RelatedChunkRead(BaseModel):
    chunk_id: str
    section_label: str | None
    page_start: int | None
    page_end: int | None
    text: str


class ChatResponse(BaseModel):
    answer: str
    related_chunks: list[RelatedChunkRead]


class ChatMessageRead(BaseModel):
    id: str
    document_id: str
    role: ChatRole
    content: str
    created_at: datetime
```

- [ ] **Step 5: Add chat repository helper**

Append to `backend/app/db/repositories.py`:

```python
import json

from backend.app.db.models import ChatMessage, ChatRole


class ChatRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_message(
        self,
        *,
        document_id: str,
        role: ChatRole,
        content: str,
        related_chunks: list[dict] | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            document_id=document_id,
            role=role,
            content=content,
            related_chunks_json=json.dumps(related_chunks or [], ensure_ascii=False),
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def list_messages(self, document_id: str) -> list[ChatMessage]:
        return list(
            self.session.exec(
                select(ChatMessage)
                .where(ChatMessage.document_id == document_id)
                .order_by(ChatMessage.created_at)
            ).all()
        )
```

- [ ] **Step 6: Add chat endpoints**

In `backend/app/api/documents.py`, import chat classes and add endpoints:

```python
from backend.app.core.config import get_settings
from backend.app.db.repositories import ChatRepository
from backend.app.schemas.documents import ChatMessageRead, ChatRequest, ChatResponse, RelatedChunkRead
from backend.app.services.chat_engine import answer_question
from backend.app.services.model_client import ModelClient
from backend.app.db.models import ChatRole
```

Append below note endpoint:

```python
@router.get("/{document_id}/chat", response_model=list[ChatMessageRead])
def list_chat(document_id: str, session: Session = Depends(get_session)):
    return ChatRepository(session).list_messages(document_id)


@router.post("/{document_id}/chat", response_model=ChatResponse)
async def chat(
    document_id: str,
    payload: ChatRequest,
    session: Session = Depends(get_session),
):
    document = DocumentRepository(session).get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    settings = get_settings()
    client = ModelClient(
        base_url=settings.api_base_url,
        api_key=settings.api_key,
        model=settings.chat_model,
        timeout_seconds=settings.request_timeout_seconds,
        temperature=settings.temperature,
    )
    ChatRepository(session).add_message(
        document_id=document_id,
        role=ChatRole.USER,
        content=payload.question,
    )
    result = await answer_question(
        session=session,
        document_id=document_id,
        question=payload.question,
        model_client=client,
    )
    related = [
        {
            "chunk_id": chunk.chunk_id,
            "section_label": chunk.section_label,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "text": chunk.text,
        }
        for chunk in result.related_chunks
    ]
    ChatRepository(session).add_message(
        document_id=document_id,
        role=ChatRole.ASSISTANT,
        content=result.answer,
        related_chunks=related,
    )
    return ChatResponse(
        answer=result.answer,
        related_chunks=[RelatedChunkRead(**item) for item in related],
    )
```

- [ ] **Step 7: Run tests**

Run:

```bash
pytest backend/tests/test_chat_engine.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 8: Commit**

```bash
git add backend/app backend/tests/test_chat_engine.py
git commit -m "feat: add grounded document chat"
```

---

### Task 12: End-to-End Processing Pipeline

**Files:**
- Modify: `backend/app/services/job_manager.py`
- Modify: `backend/app/api/documents.py`
- Modify: `backend/app/db/repositories.py`
- Test: `backend/tests/test_job_manager.py`

- [ ] **Step 1: Write processing orchestration test with fakes**

Append to `backend/tests/test_job_manager.py`:

```python
import pytest

from backend.app.db.models import Note, NoteKind
from backend.app.services.job_manager import persist_generated_notes


@pytest.mark.asyncio
async def test_persist_generated_notes_saves_both_notes(tmp_path):
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        document = Document(title="Demo", source_type=SourceType.UPLOADED_PDF)
        session.add(document)
        session.commit()
        session.refresh(document)
        structured = tmp_path / "structured_reading_note.md"
        deep = tmp_path / "deep_reading_note.md"
        structured.write_text("# 全文理解", encoding="utf-8")
        deep.write_text("# 整篇精读", encoding="utf-8")

        persist_generated_notes(
            session=session,
            document_id=document.id,
            structured_markdown="# 全文理解",
            structured_path=structured,
            deep_markdown="# 整篇精读",
            deep_path=deep,
        )

        notes = session.query(Note).all()
        assert {note.kind for note in notes} == {
            NoteKind.STRUCTURED_READING,
            NoteKind.DEEP_READING,
        }
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest backend/tests/test_job_manager.py -q
```

Expected: fails because `persist_generated_notes` is missing.

- [ ] **Step 3: Add note persistence helper**

Modify `backend/app/services/job_manager.py`:

```python
from pathlib import Path

from sqlmodel import Session

from backend.app.db.models import Document, DocumentStatus, NoteKind
from backend.app.db.repositories import DocumentRepository, NoteRepository


def mark_failed(session: Session, document: Document, message: str) -> None:
    DocumentRepository(session).update_status(
        document,
        DocumentStatus.FAILED,
        error_message=message,
    )


def set_status(session: Session, document: Document, status: DocumentStatus) -> None:
    DocumentRepository(session).update_status(document, status, error_message=None)


def persist_generated_notes(
    *,
    session: Session,
    document_id: str,
    structured_markdown: str,
    structured_path: Path,
    deep_markdown: str,
    deep_path: Path,
) -> None:
    repo = NoteRepository(session)
    repo.replace_note(
        document_id=document_id,
        kind=NoteKind.STRUCTURED_READING,
        markdown=structured_markdown,
        path=str(structured_path),
    )
    repo.replace_note(
        document_id=document_id,
        kind=NoteKind.DEEP_READING,
        markdown=deep_markdown,
        path=str(deep_path),
    )
```

- [ ] **Step 4: Add processing pipeline function**

Append to `backend/app/services/job_manager.py`:

```python
from backend.app.core.paths import document_dir
from backend.app.db.fts import rebuild_document_fts
from backend.app.db.models import Chunk
from backend.app.db.repositories import ChunkRepository, FigureRepository, SectionRepository
from backend.app.services.chunker import chunk_section_text
from backend.app.services.figure_extractor import extract_pdf_figures
from backend.app.services.html_parser import parse_html_article
from backend.app.services.model_client import ModelClient
from backend.app.services.note_generator import generate_notes
from backend.app.services.pdf_parser import parse_pdf


async def process_existing_source(
    *,
    session: Session,
    document: Document,
    source_path: Path,
    model_client: ModelClient,
) -> None:
    try:
        set_status(session, document, DocumentStatus.PARSING)
        if source_path.suffix.lower() == ".pdf":
            parsed = parse_pdf(source_path)
            set_status(session, document, DocumentStatus.EXTRACTING_FIGURES)
            extracted_figures = extract_pdf_figures(document.id, source_path)
        else:
            parsed = parse_html_article(source_path)
            extracted_figures = []

        section_rows = SectionRepository(session).replace_sections(
            document.id,
            parsed.sections,
        )
        FigureRepository(session).replace_figures(document.id, extracted_figures)

        chunk_drafts = []
        for section_row in section_rows:
            label = section_row.title
            chunk_drafts.extend(
                chunk_section_text(
                    document_id=document.id,
                    section_id=section_row.id,
                    section_label=label,
                    text=section_row.text,
                    page_start=section_row.page_start,
                    page_end=section_row.page_end,
                )
            )
        ChunkRepository(session).replace_chunks(document.id, chunk_drafts)

        set_status(session, document, DocumentStatus.GENERATING_STRUCTURED_READING)
        set_status(session, document, DocumentStatus.GENERATING_DEEP_READING)
        notes = await generate_notes(
            document_id=document.id,
            parsed=parsed,
            figures=extracted_figures,
            output_dir=document_dir(document.id),
            model_client=model_client,
        )
        persist_generated_notes(
            session=session,
            document_id=document.id,
            structured_markdown=notes.structured_markdown,
            structured_path=notes.structured_path,
            deep_markdown=notes.deep_markdown,
            deep_path=notes.deep_path,
        )

        set_status(session, document, DocumentStatus.INDEXING)
        rebuild_document_fts(session, document.id)
        set_status(session, document, DocumentStatus.COMPLETED)
    except Exception as exc:
        mark_failed(session, document, str(exc))
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest backend/tests/test_job_manager.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/job_manager.py backend/tests/test_job_manager.py
git commit -m "feat: orchestrate document processing"
```

---

### Task 13: Frontend Scaffold and API Client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: Add frontend package**

Create `frontend/package.json`:

```json
{
  "name": "paper-reader-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc && vite build",
    "preview": "vite preview --host 127.0.0.1"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "lucide-react": "^0.468.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-markdown": "^9.0.1",
    "vite": "^5.4.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "typescript": "^5.5.4"
  }
}
```

- [ ] **Step 2: Add Vite config and TypeScript config**

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PaperReader</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": []
}
```

Create `frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000"
    }
  }
});
```

- [ ] **Step 3: Add API client**

Create `frontend/src/api/client.ts`:

```ts
export type DocumentStatus =
  | "queued"
  | "fetching"
  | "parsing"
  | "extracting_figures"
  | "generating_structured_reading"
  | "generating_deep_reading"
  | "indexing"
  | "completed"
  | "failed";

export type SourceType = "uploaded_pdf" | "pdf_url" | "arxiv" | "html_article";

export interface DocumentRead {
  id: string;
  title: string;
  source_type: SourceType;
  original_url: string | null;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface NoteRead {
  document_id: string;
  kind: "structured_reading" | "deep_reading";
  markdown: string;
}

export interface ChatMessageRead {
  id: string;
  document_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatResponse {
  answer: string;
  related_chunks: Array<{
    chunk_id: string;
    section_label: string | null;
    page_start: number | null;
    page_end: number | null;
    text: string;
  }>;
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listDocuments: () => request<DocumentRead[]>("/api/documents"),
  getDocument: (id: string) => request<DocumentRead>(`/api/documents/${id}`),
  importUrl: (value: string) =>
    request<DocumentRead>("/api/documents/import-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value })
    }),
  uploadPdf: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentRead>("/api/documents/upload", {
      method: "POST",
      body: form
    });
  },
  getNote: (id: string, kind: "structured_reading" | "deep_reading") =>
    request<NoteRead>(`/api/documents/${id}/notes/${kind}`),
  listChat: (id: string) => request<ChatMessageRead[]>(`/api/documents/${id}/chat`),
  sendChat: (id: string, question: string) =>
    request<ChatResponse>(`/api/documents/${id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    })
};
```

- [ ] **Step 4: Add app entry**

Create `frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

Create `frontend/src/App.tsx`:

```tsx
export function App() {
  return (
    <main className="app-shell">
      <section className="sidebar">PaperReader</section>
      <section className="reader">选择或导入一篇文章</section>
      <section className="chat">当前文章聊天</section>
    </main>
  );
}
```

- [ ] **Step 5: Add base styles**

Create `frontend/src/styles.css`:

```css
:root {
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  color: #202124;
  background: #f6f7f9;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}

button,
input,
textarea {
  font: inherit;
}

.app-shell {
  display: grid;
  grid-template-columns: 280px minmax(360px, 1fr) 360px;
  height: 100vh;
  min-width: 960px;
  background: #f6f7f9;
}

.sidebar,
.reader,
.chat {
  min-width: 0;
  overflow: auto;
  border-right: 1px solid #d9dde5;
  background: #ffffff;
}

.sidebar,
.chat {
  padding: 16px;
}

.reader {
  padding: 24px 32px;
}
```

- [ ] **Step 6: Build frontend**

Run:

```bash
cd frontend
npm install
npm run build
```

Expected:

```text
✓ built
```

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "feat: scaffold frontend app"
```

---

### Task 14: Frontend Workspace Components

**Files:**
- Create: `frontend/src/components/ImportBox.tsx`
- Create: `frontend/src/components/DocumentList.tsx`
- Create: `frontend/src/components/NoteViewer.tsx`
- Create: `frontend/src/components/ChatPanel.tsx`
- Create: `frontend/src/components/SettingsDialog.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add import component**

Create `frontend/src/components/ImportBox.tsx`:

```tsx
import { Link, Upload } from "lucide-react";
import { FormEvent, useState } from "react";

interface ImportBoxProps {
  onImportUrl(value: string): Promise<void>;
  onUpload(file: File): Promise<void>;
}

export function ImportBox({ onImportUrl, onUpload }: ImportBoxProps) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitUrl(event: FormEvent) {
    event.preventDefault();
    if (!value.trim()) return;
    setBusy(true);
    try {
      await onImportUrl(value.trim());
      setValue("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="import-box">
      <form onSubmit={submitUrl} className="import-row">
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          aria-label="arXiv、PDF 或网页链接"
        />
        <button type="submit" disabled={busy} title="导入链接">
          <Link size={18} />
        </button>
      </form>
      <label className="upload-button" title="上传 PDF">
        <Upload size={18} />
        <span>上传 PDF</span>
        <input
          type="file"
          accept="application/pdf"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void onUpload(file);
          }}
        />
      </label>
    </div>
  );
}
```

- [ ] **Step 2: Add document list component**

Create `frontend/src/components/DocumentList.tsx`:

```tsx
import type { DocumentRead } from "../api/client";

interface DocumentListProps {
  documents: DocumentRead[];
  selectedId: string | null;
  onSelect(id: string): void;
}

export function DocumentList({ documents, selectedId, onSelect }: DocumentListProps) {
  return (
    <div className="document-list">
      {documents.map((document) => (
        <button
          key={document.id}
          className={`document-item ${selectedId === document.id ? "selected" : ""}`}
          onClick={() => onSelect(document.id)}
        >
          <span className="document-title">{document.title}</span>
          <span className={`status status-${document.status}`}>{document.status}</span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Add note viewer**

Create `frontend/src/components/NoteViewer.tsx`:

```tsx
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, type DocumentRead } from "../api/client";

interface NoteViewerProps {
  document: DocumentRead | null;
}

export function NoteViewer({ document }: NoteViewerProps) {
  const [tab, setTab] = useState<"structured_reading" | "deep_reading">(
    "structured_reading"
  );
  const [markdown, setMarkdown] = useState("");

  useEffect(() => {
    let cancelled = false;
    setMarkdown("");
    if (!document || document.status !== "completed") return;
    api
      .getNote(document.id, tab)
      .then((note) => {
        if (!cancelled) setMarkdown(note.markdown);
      })
      .catch((error) => {
        if (!cancelled) setMarkdown(`无法读取笔记：${error.message}`);
      });
    return () => {
      cancelled = true;
    };
  }, [document, tab]);

  if (!document) {
    return <div className="empty-state">选择或导入一篇文章</div>;
  }

  if (document.status === "failed") {
    return <div className="error-state">{document.error_message}</div>;
  }

  if (document.status !== "completed") {
    return <div className="empty-state">处理中：{document.status}</div>;
  }

  return (
    <div className="note-viewer">
      <div className="tabs">
        <button
          className={tab === "structured_reading" ? "active" : ""}
          onClick={() => setTab("structured_reading")}
        >
          全文理解
        </button>
        <button
          className={tab === "deep_reading" ? "active" : ""}
          onClick={() => setTab("deep_reading")}
        >
          整篇精读
        </button>
      </div>
      <article className="markdown-body">
        <ReactMarkdown>{markdown}</ReactMarkdown>
      </article>
    </div>
  );
}
```

- [ ] **Step 4: Add chat panel**

Create `frontend/src/components/ChatPanel.tsx`:

```tsx
import { Send } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { api, type ChatMessageRead, type DocumentRead } from "../api/client";

interface ChatPanelProps {
  document: DocumentRead | null;
}

export function ChatPanel({ document }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessageRead[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setMessages([]);
    if (!document) return;
    api.listChat(document.id).then((items) => {
      if (!cancelled) setMessages(items);
    });
    return () => {
      cancelled = true;
    };
  }, [document]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!document || !question.trim()) return;
    const text = question.trim();
    setQuestion("");
    setBusy(true);
    try {
      const response = await api.sendChat(document.id, text);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          document_id: document.id,
          role: "user",
          content: text,
          created_at: new Date().toISOString()
        },
        {
          id: crypto.randomUUID(),
          document_id: document.id,
          role: "assistant",
          content: response.answer,
          created_at: new Date().toISOString()
        }
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            {message.content}
          </div>
        ))}
      </div>
      <form onSubmit={submit} className="chat-form">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          aria-label="问当前文章"
          disabled={!document || document.status !== "completed"}
        />
        <button type="submit" disabled={busy || !question.trim()} title="发送">
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 5: Add settings dialog shell**

Create `frontend/src/components/SettingsDialog.tsx`:

```tsx
import { X } from "lucide-react";

interface SettingsDialogProps {
  open: boolean;
  onClose(): void;
}

export function SettingsDialog({ open, onClose }: SettingsDialogProps) {
  if (!open) return null;
  return (
    <div className="dialog-backdrop">
      <section className="settings-dialog">
        <header>
          <h2>模型设置</h2>
          <button onClick={onClose} title="关闭">
            <X size={18} />
          </button>
        </header>
        <p>设置表单在后续任务接入 `/api/settings`。</p>
      </section>
    </div>
  );
}
```

- [ ] **Step 6: Wire components in App**

Modify `frontend/src/App.tsx`:

```tsx
import { Settings } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, type DocumentRead } from "./api/client";
import { ChatPanel } from "./components/ChatPanel";
import { DocumentList } from "./components/DocumentList";
import { ImportBox } from "./components/ImportBox";
import { NoteViewer } from "./components/NoteViewer";
import { SettingsDialog } from "./components/SettingsDialog";

export function App() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  async function refreshDocuments() {
    const list = await api.listDocuments();
    setDocuments(list);
    setSelectedId((current) => current ?? list[0]?.id ?? null);
  }

  useEffect(() => {
    void refreshDocuments();
    const timer = window.setInterval(() => void refreshDocuments(), 3000);
    return () => window.clearInterval(timer);
  }, []);

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedId) ?? null,
    [documents, selectedId]
  );

  return (
    <main className="app-shell">
      <section className="sidebar">
        <header className="sidebar-header">
          <h1>PaperReader</h1>
          <button onClick={() => setSettingsOpen(true)} title="模型设置">
            <Settings size={18} />
          </button>
        </header>
        <ImportBox
          onImportUrl={async (value) => {
            const document = await api.importUrl(value);
            await refreshDocuments();
            setSelectedId(document.id);
          }}
          onUpload={async (file) => {
            const document = await api.uploadPdf(file);
            await refreshDocuments();
            setSelectedId(document.id);
          }}
        />
        <DocumentList
          documents={documents}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
      </section>
      <section className="reader">
        <NoteViewer document={selectedDocument} />
      </section>
      <section className="chat">
        <ChatPanel document={selectedDocument} />
      </section>
      <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </main>
  );
}
```

- [ ] **Step 7: Extend styles**

Append to `frontend/src/styles.css`:

```css
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sidebar-header h1 {
  margin: 0;
  font-size: 18px;
}

button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #c7ccd6;
  border-radius: 6px;
  background: #ffffff;
  color: #202124;
  cursor: pointer;
  min-height: 36px;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.import-box {
  display: grid;
  gap: 10px;
  margin: 16px 0;
}

.import-row {
  display: grid;
  grid-template-columns: 1fr 40px;
  gap: 8px;
}

.import-row input {
  min-width: 0;
  border: 1px solid #c7ccd6;
  border-radius: 6px;
  padding: 8px 10px;
}

.upload-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 38px;
  border: 1px dashed #8b95a7;
  border-radius: 6px;
  cursor: pointer;
}

.upload-button input {
  display: none;
}

.document-list {
  display: grid;
  gap: 8px;
}

.document-item {
  display: grid;
  align-items: start;
  justify-content: stretch;
  text-align: left;
  gap: 6px;
  width: 100%;
  padding: 10px;
}

.document-item.selected {
  border-color: #2864d8;
  background: #eef4ff;
}

.document-title {
  overflow-wrap: anywhere;
  font-size: 14px;
}

.status {
  color: #5f6b7a;
  font-size: 12px;
}

.status-completed {
  color: #126c3a;
}

.status-failed {
  color: #b42318;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 18px;
}

.tabs button {
  padding: 0 14px;
}

.tabs .active {
  background: #202124;
  color: #ffffff;
  border-color: #202124;
}

.markdown-body {
  max-width: 860px;
  line-height: 1.72;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
  line-height: 1.25;
}

.empty-state,
.error-state {
  color: #5f6b7a;
}

.error-state {
  color: #b42318;
}

.chat-panel {
  display: grid;
  grid-template-rows: 1fr auto;
  height: calc(100vh - 32px);
  gap: 12px;
}

.chat-messages {
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 10px;
}

.message {
  border-radius: 8px;
  padding: 10px 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.message.user {
  background: #eef4ff;
}

.message.assistant {
  background: #f1f3f5;
}

.chat-form {
  display: grid;
  grid-template-columns: 1fr 40px;
  gap: 8px;
}

.chat-form textarea {
  min-height: 72px;
  resize: vertical;
  border: 1px solid #c7ccd6;
  border-radius: 6px;
  padding: 8px 10px;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgb(32 33 36 / 35%);
}

.settings-dialog {
  width: min(520px, calc(100vw - 32px));
  background: #ffffff;
  border-radius: 8px;
  padding: 18px;
  box-shadow: 0 20px 50px rgb(32 33 36 / 20%);
}

.settings-dialog header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.settings-dialog h2 {
  margin: 0;
  font-size: 18px;
}
```

- [ ] **Step 8: Build frontend**

Run:

```bash
cd frontend
npm run build
```

Expected:

```text
✓ built
```

- [ ] **Step 9: Commit**

```bash
git add frontend/src
git commit -m "feat: add reader workspace UI"
```

---

### Task 15: Settings UI and Document Actions

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/SettingsDialog.tsx`
- Modify: `backend/app/api/documents.py`
- Modify: `backend/app/db/repositories.py`
- Test: `backend/tests/test_api_documents.py`

- [ ] **Step 1: Add delete API test**

Append to `backend/tests/test_api_documents.py`:

```python
def test_delete_document_removes_it_from_list():
    client = TestClient(create_app())
    created = client.post("/api/documents/import-url", json={"value": "2401.12345"}).json()

    response = client.delete(f"/api/documents/{created['id']}")

    assert response.status_code == 204
    assert client.get("/api/documents").json() == []
```

- [ ] **Step 2: Run test and confirm failure**

Run:

```bash
pytest backend/tests/test_api_documents.py::test_delete_document_removes_it_from_list -q
```

Expected: fails because delete endpoint is missing.

- [ ] **Step 3: Add delete repository method**

Add inside `DocumentRepository` in `backend/app/db/repositories.py`:

```python
    def delete_document(self, document_id: str) -> bool:
        document = self.session.get(Document, document_id)
        if document is None:
            return False
        self.session.delete(document)
        self.session.commit()
        return True
```

- [ ] **Step 4: Add delete endpoint**

Append to `backend/app/api/documents.py`:

```python
@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, session: Session = Depends(get_session)):
    deleted = DocumentRepository(session).delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return None
```

- [ ] **Step 5: Extend frontend API client for settings and delete**

Append types and methods in `frontend/src/api/client.ts`:

```ts
export interface SettingsRead {
  api_base_url: string;
  chat_model: string;
  request_timeout_seconds: number;
  temperature: number;
  api_key_configured: boolean;
}

export interface SettingsUpdate {
  api_base_url: string;
  api_key: string;
  chat_model: string;
  request_timeout_seconds: number;
  temperature: number;
}
```

Add to `api`:

```ts
  deleteDocument: (id: string) =>
    fetch(`/api/documents/${id}`, { method: "DELETE" }).then((response) => {
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
    }),
  getSettings: () => request<SettingsRead>("/api/settings"),
  updateSettings: (payload: SettingsUpdate) =>
    request<SettingsRead>("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
```

Ensure commas are valid in the object literal.

- [ ] **Step 6: Replace settings dialog with form**

Modify `frontend/src/components/SettingsDialog.tsx`:

```tsx
import { X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";

interface SettingsDialogProps {
  open: boolean;
  onClose(): void;
}

export function SettingsDialog({ open, onClose }: SettingsDialogProps) {
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [chatModel, setChatModel] = useState("");
  const [timeout, setTimeoutValue] = useState(120);
  const [temperature, setTemperature] = useState(0.2);

  useEffect(() => {
    if (!open) return;
    api.getSettings().then((settings) => {
      setApiBaseUrl(settings.api_base_url);
      setChatModel(settings.chat_model);
      setTimeoutValue(settings.request_timeout_seconds);
      setTemperature(settings.temperature);
      setApiKey("");
    });
  }, [open]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    await api.updateSettings({
      api_base_url: apiBaseUrl,
      api_key: apiKey,
      chat_model: chatModel,
      request_timeout_seconds: timeout,
      temperature
    });
    onClose();
  }

  if (!open) return null;
  return (
    <div className="dialog-backdrop">
      <form className="settings-dialog" onSubmit={submit}>
        <header>
          <h2>模型设置</h2>
          <button type="button" onClick={onClose} title="关闭">
            <X size={18} />
          </button>
        </header>
        <label>
          Base URL
          <input value={apiBaseUrl} onChange={(event) => setApiBaseUrl(event.target.value)} />
        </label>
        <label>
          API Key
          <input
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            type="password"
            aria-label="API Key，留空会清除应用内 key，继续使用 .env 默认值"
          />
        </label>
        <label>
          Chat Model
          <input value={chatModel} onChange={(event) => setChatModel(event.target.value)} />
        </label>
        <label>
          Timeout Seconds
          <input
            value={timeout}
            onChange={(event) => setTimeoutValue(Number(event.target.value))}
            type="number"
            min={5}
            max={600}
          />
        </label>
        <label>
          Temperature
          <input
            value={temperature}
            onChange={(event) => setTemperature(Number(event.target.value))}
            type="number"
            min={0}
            max={2}
            step={0.1}
          />
        </label>
        <button type="submit">保存</button>
      </form>
    </div>
  );
}
```

- [ ] **Step 7: Run backend and frontend checks**

Run:

```bash
pytest backend/tests/test_api_documents.py -q
cd frontend
npm run build
```

Expected:

```text
backend document tests pass
frontend build succeeds
```

- [ ] **Step 8: Commit**

```bash
git add backend/app backend/tests frontend/src
git commit -m "feat: add settings and document actions"
```

---

### Task 16: Manual End-to-End Verification and GitHub Sync

**Files:**
- Modify: `README.md`
- Create if useful: `docs/superpowers/manual-test-notes.md`

- [ ] **Step 1: Update README with full run instructions**

Modify `README.md` so it contains:

```markdown
## Run Backend

```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Model Configuration

The backend reads `.env` defaults:

```bash
PAPER_READER_API_BASE_URL=https://api.openai.com/v1
PAPER_READER_API_KEY=...
PAPER_READER_CHAT_MODEL=gpt-4.1-mini
```

The settings dialog can override these values locally.

## Supported Inputs

- Text-based PDF upload.
- PDF URL.
- arXiv link or ID.
- Readable web article URL.

Scanned PDFs without extractable text are not supported in the first version.
```

- [ ] **Step 2: Run full automated verification**

Run:

```bash
pytest -q
cd frontend
npm run build
```

Expected:

```text
all backend tests pass
frontend build succeeds
```

- [ ] **Step 3: Start both servers**

In terminal 1:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

In terminal 2:

```bash
cd frontend
npm run dev
```

Expected:

```text
Backend: http://127.0.0.1:8000
Frontend: http://127.0.0.1:5173
```

- [ ] **Step 4: Manual browser verification**

Open:

```text
http://127.0.0.1:5173
```

Verify:

- The three-column workspace loads.
- The settings dialog opens and saves model settings.
- A PDF upload creates a document row.
- A URL import creates a document row.
- Completed documents show `全文理解` and `整篇精读` tabs when notes exist.
- Chat input is disabled until the selected document is completed.

- [ ] **Step 5: Fix GitHub SSH known_hosts if needed**

Run:

```bash
mkdir -p ~/.ssh
ssh-keyscan github.com >> ~/.ssh/known_hosts
git ls-remote git@github.com:Goldfish728/PaperReader.git HEAD
```

Expected:

```text
git ls-remote prints a commit hash or no output for an empty repository, without Host key verification failed
```

- [ ] **Step 6: Commit README updates**

```bash
git add README.md
git commit -m "docs: add local run instructions"
```

- [ ] **Step 7: Push to GitHub**

Run:

```bash
git status --short
git push -u origin main
```

Expected:

```text
branch 'main' set up to track 'origin/main'
```

---

## Self-Review

Spec coverage:

- Local FastAPI + React app: covered by Tasks 1, 13, and 14.
- Upload PDF, PDF URL, arXiv, and web URL source classification: covered by Tasks 3 and 4.
- Text-based PDF and HTML parsing: covered by Task 5.
- Original figures and captions: covered by Task 6.
- Structured full-text understanding and deep-reading note files: covered by Task 9.
- Local SQLite and filesystem persistence: covered by Tasks 2, 4, 7, 9, 10, and 12.
- SQLite FTS5/BM25 retrieval without vector database: covered by Task 7.
- Current-document chat: covered by Task 11.
- Three-column UI with two note tabs and chat: covered by Tasks 13 and 14.
- `.env` defaults plus in-app settings override: covered by Tasks 2 and 15.
- Error states and processing statuses: covered by Tasks 10 and 12.
- GitHub remote sync: covered by Task 16.

Completion marker scan:

- The plan avoids unresolved marker words and vague unfinished instructions.
- Deferred product features remain outside implementation scope and are not listed as plan steps.

Type consistency:

- Backend source types match `SourceType` enum values.
- Note kinds match `NoteKind` enum values and frontend note tab values.
- Document statuses match the design spec and frontend union type.
- Chat roles match backend enum values and frontend message type.
