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
