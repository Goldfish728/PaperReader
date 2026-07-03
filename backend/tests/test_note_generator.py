from pathlib import Path

import pytest

from backend.app.services.model_client import ChatMessage
from backend.app.services.note_generator import generate_notes
from backend.app.services.pdf_parser import ParsedDocument, ParsedSection


class FakeModelClient:
    def __init__(self):
        self.calls = 0

    async def complete(self, messages: list[ChatMessage]) -> str:
        self.calls += 1
        if self.calls == 1:
            return "# 全文理解\n\n## 1 Introduction\n\n中文结构化说明。"
        return "# 整篇精读\n\n## 核心贡献\n\n中文精读说明。"


class CapturingModelClient:
    def __init__(self):
        self.calls: list[list[ChatMessage]] = []

    async def complete(self, messages: list[ChatMessage]) -> str:
        self.calls.append(messages)
        return "# mock"


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


@pytest.mark.asyncio
async def test_generate_notes_uses_deep_paper_reading_prompt(tmp_path: Path):
    parsed = ParsedDocument(
        title="Demo Paper",
        abstract="This paper studies evaluation-driven customer support agents.",
        raw_text="1 Introduction\nThis paper introduces a method.",
        sections=[
            ParsedSection(
                number="1",
                title="1 Introduction",
                level=1,
                order=0,
                page_start=1,
                page_end=2,
                text="This paper introduces a method and its evidence chain.",
            )
        ],
    )
    model_client = CapturingModelClient()

    await generate_notes(
        document_id="doc1",
        parsed=parsed,
        figures=[],
        output_dir=tmp_path,
        model_client=model_client,
    )

    structured_prompt = "\n".join(message.content for message in model_client.calls[0])
    deep_prompt = "\n".join(message.content for message in model_client.calls[1])

    assert "本节在回答什么问题" in structured_prompt
    assert "原文逻辑推进" in structured_prompt
    assert "关键概念/术语" in structured_prompt
    assert "证据链" in structured_prompt
    assert "原文材料不足，无法确认" in structured_prompt
    assert "图表怎么读" in deep_prompt
    assert "局限" in deep_prompt
    assert "可复用启发" in deep_prompt


@pytest.mark.asyncio
async def test_generate_notes_sends_abstract_and_richer_section_material(tmp_path: Path):
    important_tail = "TAIL_EVIDENCE: ablation shows the judge prompt improves agreement."
    long_text = "A" * 3500 + important_tail
    parsed = ParsedDocument(
        title="Demo Paper",
        abstract="The abstract states the central thesis.",
        raw_text=long_text,
        sections=[
            ParsedSection(
                number="2",
                title="2 Method",
                level=1,
                order=0,
                page_start=3,
                page_end=5,
                text=long_text,
            )
        ],
    )
    model_client = CapturingModelClient()

    await generate_notes(
        document_id="doc1",
        parsed=parsed,
        figures=[],
        output_dir=tmp_path,
        model_client=model_client,
    )

    first_user_prompt = model_client.calls[0][1].content
    assert "The abstract states the central thesis." in first_user_prompt
    assert important_tail in first_user_prompt
    assert "页码：3-5" in first_user_prompt
