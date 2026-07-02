import re
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
    units = _text_units(text, max_chars=max_chars)
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

    for unit in units:
        if current and current_len + len(unit) > max_chars:
            flush()
        current.append(unit)
        current_len += len(unit)
    flush()
    return chunks


def _text_units(text: str, max_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n") if paragraph.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            units.append(paragraph)
            continue
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph)
            if sentence.strip()
        ]
        for sentence in sentences:
            if len(sentence) <= max_chars:
                units.append(sentence)
            else:
                units.extend(_split_long_text(sentence, max_chars=max_chars))
    return units


def _split_long_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        word_len = len(word)
        if current and current_len + 1 + word_len > max_chars:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
        current.append(word)
        current_len += word_len + (1 if current_len else 0)
    if current:
        chunks.append(" ".join(current))
    return chunks
