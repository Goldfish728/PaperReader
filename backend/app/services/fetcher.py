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
    content = await file.read()
    if not content.startswith(b"%PDF"):
        raise ValueError("Uploaded file does not look like a PDF.")
    path = document_dir(document_id) / "original.pdf"
    path.write_bytes(content)
    return path


async def download_pdf(
    document_id: str,
    url: str,
    timeout_seconds: int = 60,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Path:
    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=True,
        transport=transport,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
    content = response.content
    if not content.startswith(b"%PDF"):
        raise ValueError("URL did not return a PDF file.")
    path = document_dir(document_id) / "original.pdf"
    path.write_bytes(content)
    return path


async def download_html(
    document_id: str,
    url: str,
    timeout_seconds: int = 60,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Path:
    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=True,
        transport=transport,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
    content = response.content
    content_type = response.headers.get("content-type", "").lower().split(";")[0].strip()
    is_text_response = content_type.startswith("text/") or "html" in content_type
    if content.startswith(b"%PDF") or "pdf" in content_type or b"\x00" in content[:1024]:
        raise ValueError("URL did not return an HTML document.")
    if content_type and not is_text_response:
        raise ValueError("URL did not return an HTML document.")
    path = document_dir(document_id) / "source.html"
    path.write_text(response.text, encoding=response.encoding or "utf-8")
    return path
