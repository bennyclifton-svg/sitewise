import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai import AgentRunResult

from app.assistant.outputs import Citation, EvidenceLabel, GroundedAnswer
from app.chat.orchestrator import run_chat_turn
from app.retrieval.schemas import SourcePassage
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
THREAD_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def test_run_chat_turn_uses_whole_document_path() -> None:
    session = AsyncMock()
    document_id = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    passage = SourcePassage(
        chunk_id=document_id,
        document_id=document_id,
        chunk_index=0,
        content="A Project Management Plan (PMP) defines how the project will be managed.",
        page_or_section=None,
        project="sitewise-platform",
        phase="reference",
        source_type="reference",
        document_class="reference_guide",
        filename="guide.md",
        relative_path="seed/guide.md",
        document_metadata={"knowledge_scope": "platform"},
        chunk_metadata={"whole_document": True},
        score=1.0,
    )
    grounded = GroundedAnswer(
        answer="A PMP is a project management plan.",
        citations=[
            Citation(
                chunk_id=document_id,
                document_id=document_id,
                excerpt="A Project Management Plan (PMP) defines how the project will be managed.",
                filename="guide.md",
                project="sitewise-platform",
                source_type="reference",
                label=EvidenceLabel.FACT,
            )
        ],
    )
    mock_result = MagicMock(spec=AgentRunResult)
    mock_result.output = grounded
    mock_run = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.chat.orchestrator.load_platform_whole_documents",
            new=AsyncMock(return_value=[passage]),
        ),
        patch("app.chat.orchestrator.platform_qa_agent.run", new=mock_run),
    ):
        result = run_async(
            run_chat_turn(
                session,
                user_id=USER_ID,
                thread_id=THREAD_ID,
                user_text="what is a PMP",
            )
        )

    assert "PMP" in result.answer
    assert result.citations
    mock_run.assert_called_once()
    assert mock_run.call_args.kwargs["usage_limits"].request_limit == 5
