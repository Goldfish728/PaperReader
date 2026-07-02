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
