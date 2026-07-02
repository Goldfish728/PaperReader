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
    if not pages:
        return []

    sections: list[ParsedSection] = []
    current_title = "S1 Full Text"
    current_number = "S1"
    current_level = 1
    current_page_start: int | None = pages[0][0]
    current_lines: list[str] = []

    def flush(page_end: int | None) -> None:
        text = "\n".join(current_lines).strip()
        if not text:
            return
        sections.append(
            ParsedSection(
                number=current_number,
                title=current_title,
                level=current_level,
                order=len(sections),
                page_start=current_page_start,
                page_end=page_end,
                text=text,
            )
        )

    for page_number, page_text in pages:
        for line in page_text.splitlines():
            level = detect_heading_level(line)
            if level is not None:
                if current_lines:
                    flush(page_number)
                stripped = " ".join(line.strip().split())
                number, _title = stripped.split(" ", 1)
                current_number = number
                current_title = stripped
                current_level = level
                current_page_start = page_number
                current_lines = [line]
            else:
                current_lines.append(line)
    flush(pages[-1][0])
    return sections
