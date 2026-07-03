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


STRUCTURED_READING_SYSTEM_PROMPT = """
你是严谨的英文论文中文精读导师。你的任务不是泛泛总结，而是帮助读者用中文真正读懂论文的写作结构、论证推进和证据链。

输出要求：
1. 严格保留原文已有标题层级、章节编号和列表层级；不要发明原文没有的章节。
2. “全文理解”不是逐句全文翻译，但要接近论文阅读笔记：
   按原文顺序解释每节在讲什么、为什么这样讲、和前后文如何衔接。
3. 每个主要章节尽量包含这些小项：
   - 本节在回答什么问题
   - 原文逻辑推进
   - 关键概念/术语
   - 方法或实验细节
   - 证据链
   - 本节结论
   - 读者应该记住什么
4. 对公式、图表、实验、消融、指标和数据，不只翻译名称，要解释它们在论证中承担什么作用。
5. 保留重要英文术语，并在第一次出现时给出中文解释。
6. 不要空泛夸赞，不要写套话，不要把常识当贡献。
7. 如果材料里没有足够证据，请明确写“原文材料不足，无法确认”，不要编造。
8. 输出中文 Markdown，标题清晰，层级稳定，便于用户按第几章第几节提问。
""".strip()


DEEP_READING_SYSTEM_PROMPT = """
你是资深研究论文导师。请基于原文材料和上一阶段全文理解，生成一份“整篇精读”。

目标是让读者读完后能回答：
1. 论文到底在解决什么问题，为什么这个问题重要？
2. 作者的核心主张和贡献是什么？
3. 方法/系统/实验设计为什么这样安排？
4. 证据链是否支撑结论，关键图表怎么读？
5. 这篇论文的局限、边界条件和可复用启发是什么？

输出结构：
- 一句话主线
- 背景与问题
- 核心贡献
- 方法机制
- 实验设计与证据链
- 关键图表怎么读
- 局限与不确定性
- 和相关思路的差异
- 可复用启发
- 读完应掌握的要点

要求：
1. 用中文解释深层逻辑，不要只改写上一阶段内容。
2. 区分“原文明确说明”“从材料可推断”“原文材料不足，无法确认”。
3. 评价要具体，围绕方法、实验、指标、假设和落地条件。
4. 不要杜撰原文没有的信息。
""".strip()


def section_digest(parsed: ParsedDocument, max_chars_per_section: int = 12000) -> str:
    blocks: list[str] = []
    if parsed.abstract:
        blocks.append(f"# Abstract\n{parsed.abstract.strip()}")
    for section in parsed.sections:
        label = section.title
        text = _clip_text(section.text, max_chars_per_section)
        page_span = _page_span(section.page_start, section.page_end)
        page_line = f"页码：{page_span}\n" if page_span else ""
        blocks.append(f"## {label}\n{page_line}{text}")
    return "\n\n".join(blocks)


def _clip_text(text: str, max_chars: int) -> str:
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    head_chars = int(max_chars * 0.72)
    tail_chars = max_chars - head_chars
    return (
        stripped[:head_chars].rstrip()
        + "\n\n[中间内容因长度省略，保留本节开头与结尾以兼顾定义、方法和结论。]\n\n"
        + stripped[-tail_chars:].lstrip()
    )


def _page_span(page_start: int | None, page_end: int | None) -> str:
    if page_start is None and page_end is None:
        return ""
    if page_start is None:
        return str(page_end)
    if page_end is None or page_end == page_start:
        return str(page_start)
    return f"{page_start}-{page_end}"


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
                content=STRUCTURED_READING_SYSTEM_PROMPT,
            ),
            ChatMessage(
                role="user",
                content=(
                    f"文档标题：{parsed.title}\n\n"
                    f"任务：生成“全文理解”。请按原文结构输出，做到中等偏深入："
                    f"不能太简略，也不要逐句全文翻译。\n\n"
                    f"章节内容：\n{digest}\n\n"
                    f"图表信息：\n{figure_text or '无可用图表信息。'}"
                ),
            ),
        ]
    )
    deep = await model_client.complete(
        [
            ChatMessage(
                role="system",
                content=DEEP_READING_SYSTEM_PROMPT,
            ),
            ChatMessage(
                role="user",
                content=(
                    f"文档标题：{parsed.title}\n\n"
                    f"任务：生成“整篇精读”。请更像论文导师讲解，不要只复述摘要。\n\n"
                    f"上一阶段生成的阅读稿：\n{structured}\n\n"
                    f"原文章节摘要材料：\n{digest}\n\n"
                    f"图表信息：\n{figure_text or '无可用图表信息。'}"
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
