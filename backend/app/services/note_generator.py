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
                    f"上一阶段生成的阅读稿：\n{structured}\n\n"
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
