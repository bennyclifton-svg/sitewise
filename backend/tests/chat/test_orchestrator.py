import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai import AgentRunResult

from app.assistant.outputs import Citation, EvidenceLabel, GroundedAnswer
from app.chat.orchestrator import run_chat_turn
from app.grounding.validator import GroundingError
from app.retrieval.catalog import CorpusProjectSummary
from app.retrieval.inventory import PlatformDocumentRow
from app.retrieval.schemas import SourcePassage
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
THREAD_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _passage() -> SourcePassage:
    chunk_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    document_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    return SourcePassage(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        content="Evaluation criteria include price and experience.",
        page_or_section="p.1",
        project="procurement-blockb",
        phase="procurement",
        source_type="project_evidence",
        document_class="evaluation",
        filename="evaluation.pdf",
        relative_path="procurement-blockb/06 EVALUATION/evaluation.pdf",
        document_metadata={"procurement_stage": "evaluation"},
        chunk_metadata=None,
        score=0.9,
    )


def test_run_chat_turn_uses_catalog_fast_path() -> None:
    session = AsyncMock()
    chunk_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    document_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    catalog = [
        CorpusProjectSummary(
            project="procurement-blockb",
            phase="procurement",
            source_type="project_evidence",
            document_count=10,
            sample_chunk_id=chunk_id,
            sample_document_id=document_id,
            sample_filename="brief.pdf",
            sample_relative_path="procurement-blockb/03 RFT/brief.pdf",
        )
    ]

    with patch(
        "app.chat.orchestrator.list_corpus_projects",
        new=AsyncMock(return_value=catalog),
    ):
        result = run_async(
            run_chat_turn(
                session,
                user_id=USER_ID,
                thread_id=THREAD_ID,
                user_text="hello, what projects are you aware of?",
            )
        )

    assert "procurement-blockb" in result.answer
    assert result.citations


def test_run_chat_turn_uses_seed_inventory_fast_path() -> None:
    session = AsyncMock()
    document_id = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    seed_rows = [
        PlatformDocumentRow(
            document_id=document_id,
            filename="guide.md",
            relative_path="seed/guide.md",
            project="sitewise-platform",
            phase="reference",
            source_type="reference",
            document_class="reference_guide",
            knowledge_kind="seed",
        )
    ]

    with patch(
        "app.chat.orchestrator.list_seed_documents",
        new=AsyncMock(return_value=seed_rows),
    ):
        result = run_async(
            run_chat_turn(
                session,
                user_id=USER_ID,
                thread_id=THREAD_ID,
                user_text="list the seed knowledge files you have ingested",
            )
        )

    assert "seed/guide.md" in result.answer
    assert result.citations


def test_run_chat_turn_validates_grounded_answer() -> None:
    session = AsyncMock()
    passage = _passage()
    grounded = GroundedAnswer(
        answer="Block B evaluation criteria include price and experience.",
        citations=[
            Citation(
                chunk_id=passage.chunk_id,
                document_id=passage.document_id,
                excerpt="Evaluation criteria include price and experience.",
                filename=passage.filename,
                project=passage.project,
                source_type=passage.source_type,
                label=EvidenceLabel.FACT,
            )
        ],
    )
    mock_result = MagicMock(spec=AgentRunResult)
    mock_result.output = grounded

    with (
        patch(
            "app.chat.orchestrator.list_corpus_projects",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.chat.orchestrator.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[passage]),
        ),
        patch("app.chat.orchestrator.agent.run", new=AsyncMock(return_value=mock_result)),
    ):
        result = run_async(
            run_chat_turn(
                session,
                user_id=USER_ID,
                thread_id=THREAD_ID,
                user_text="What are the evaluation criteria?",
            )
        )

    assert result.answer.startswith("Block B evaluation")
    assert len(result.cited_passages) == 1


def test_run_chat_turn_raises_on_bad_grounding() -> None:
    session = AsyncMock()
    passage = _passage()
    grounded = GroundedAnswer(
        answer="Unsupported claim.",
        citations=[
            Citation(
                chunk_id=uuid.uuid4(),
                document_id=passage.document_id,
                excerpt="missing",
                filename=passage.filename,
                project=passage.project,
                source_type=passage.source_type,
            )
        ],
    )
    mock_result = MagicMock(spec=AgentRunResult)
    mock_result.output = grounded

    with (
        patch(
            "app.chat.orchestrator.list_corpus_projects",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.chat.orchestrator.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[passage]),
        ),
        patch("app.chat.orchestrator.agent.run", new=AsyncMock(return_value=mock_result)),
    ):
        try:
            run_async(
                run_chat_turn(
                    session,
                    user_id=USER_ID,
                    thread_id=THREAD_ID,
                    user_text="What are the evaluation criteria?",
                )
            )
        except GroundingError:
            return
    raise AssertionError("Expected GroundingError")
