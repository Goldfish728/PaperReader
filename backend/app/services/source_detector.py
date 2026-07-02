import re
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.app.db.models import SourceType

ARXIV_NEW_STYLE_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
ARXIV_OLD_STYLE_RE = re.compile(r"^[a-z-]+(\.[a-z-]+)?/\d{7}(v\d+)?$", re.IGNORECASE)
ARXIV_HOSTS = {"arxiv.org", "www.arxiv.org"}


@dataclass(frozen=True)
class DetectedSource:
    source_type: SourceType
    normalized_value: str


def normalize_arxiv_id(value: str) -> str | None:
    stripped = value.strip()
    parsed = urlparse(stripped)
    if parsed.scheme in {"http", "https"}:
        if parsed.hostname not in ARXIV_HOSTS:
            return None
        if parsed.path.startswith("/abs/"):
            arxiv_id = parsed.path.removeprefix("/abs/")
        elif parsed.path.startswith("/pdf/"):
            arxiv_id = parsed.path.removeprefix("/pdf/").removesuffix(".pdf")
        else:
            return None
        return arxiv_id if _is_arxiv_id(arxiv_id) else None
    if _is_arxiv_id(stripped):
        return stripped
    return None


def _is_arxiv_id(value: str) -> bool:
    return bool(ARXIV_NEW_STYLE_RE.match(value) or ARXIV_OLD_STYLE_RE.match(value))


def detect_text_source(value: str) -> DetectedSource:
    stripped = value.strip()
    arxiv_id = normalize_arxiv_id(stripped)
    if arxiv_id:
        return DetectedSource(SourceType.ARXIV, arxiv_id)
    if urlparse(stripped).path.lower().endswith(".pdf"):
        return DetectedSource(SourceType.PDF_URL, stripped)
    return DetectedSource(SourceType.HTML_ARTICLE, stripped)
