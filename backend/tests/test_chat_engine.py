import pytest
from sqlmodel import Session

from backend.app.db.engine import get_engine, init_db
from backend.app.db.fts import rebuild_document_fts
from backend.app.db.models import Chunk, Document, SourceType
from backend.app.services.chat_engine import answer_question
from backend.app.services.model_client import ChatMessage


class FakeModelClient:
    async def complete(self, messages: list[ChatMessage]) -> str:
        joined = "\n".join(message.content for message in messages)
        assert "baseline accuracy" in joined
        assert "4 Experiments" in joined
        return "这个方法通过消融实验说明相比 baseline 有提升。"


@pytest.mark.asyncio
async def test_answer_question_uses_retrieved_chunks():
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        document = Document(title="Demo", source_type=SourceType.UPLOADED_PDF)
        session.add(document)
        session.commit()
        session.refresh(document)
        chunk = Chunk(
            document_id=document.id,
            section_label="4 Experiments",
            order=0,
            text="The method improves baseline accuracy in the ablation study.",
        )
        session.add(chunk)
        session.commit()
        rebuild_document_fts(session, document.id)

        result = await answer_question(
            session=session,
            document_id=document.id,
            question="这个方法相比 baseline 有什么提升？",
            model_client=FakeModelClient(),
        )

    assert "消融实验" in result.answer
    assert result.related_chunks[0].section_label == "4 Experiments"
