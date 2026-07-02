import re
from dataclasses import dataclass
from typing import Protocol

from sqlmodel import Session

from backend.app.db.fts import FtsSearchResult, search_document_chunks
from backend.app.services.model_client import ChatMessage


class CompletesChat(Protocol):
    async def complete(self, messages: list[ChatMessage]) -> str:
        raise NotImplementedError


TERM_MAPPING = {
    "基线": "baseline",
    "对比": "comparison",
    "提升": "improvement accuracy performance",
    "消融": "ablation",
    "实验": "experiment results",
    "方法": "method approach",
    "贡献": "contribution",
    "局限": "limitation",
}


@dataclass(frozen=True)
class ChatAnswer:
    answer: str
    related_chunks: list[FtsSearchResult]


async def answer_question(
    *,
    session: Session,
    document_id: str,
    question: str,
    model_client: CompletesChat,
) -> ChatAnswer:
    search_query = _build_search_query(question)
    chunks = search_document_chunks(session, document_id, search_query)
    answer = await model_client.complete(
        [
            ChatMessage(
                role="system",
                content=(
                    "你是论文阅读问答助手。请用中文回答用户问题，优先依据提供的论文片段。"
                    "如果片段不足以支持结论，请明确说明缺少相关信息。"
                ),
            ),
            ChatMessage(
                role="user",
                content=_build_prompt(question=question, chunks=chunks),
            ),
        ]
    )
    return ChatAnswer(answer=answer, related_chunks=chunks)


def _build_search_query(question: str) -> str:
    terms: list[str] = []
    for chinese, english in TERM_MAPPING.items():
        if chinese in question:
            terms.extend(english.split())
    terms.extend(re.findall(r"[A-Za-z0-9_]+", question.lower()))
    unique_terms = list(dict.fromkeys(terms))
    return " OR ".join(unique_terms)


def _build_prompt(question: str, chunks: list[FtsSearchResult]) -> str:
    if chunks:
        context = "\n\n".join(_format_chunk(index, chunk) for index, chunk in enumerate(chunks, 1))
    else:
        context = "未检索到相关片段。请基于空上下文回答；如论文信息不足，请明确说明缺少依据。"
    return (
        "请用中文回答下面的问题。\n\n"
        f"问题：{question}\n\n"
        f"检索到的论文片段：\n{context}"
    )


def _format_chunk(index: int, chunk: FtsSearchResult) -> str:
    label = chunk.section_label or "未知章节"
    page = _page_label(chunk.page_start, chunk.page_end)
    return f"[{index}] 章节：{label}\n页码：{page}\n内容：{chunk.text}"


def _page_label(page_start: int | None, page_end: int | None) -> str:
    if page_start is None and page_end is None:
        return "未知"
    if page_start == page_end or page_end is None:
        return str(page_start)
    if page_start is None:
        return str(page_end)
    return f"{page_start}-{page_end}"

