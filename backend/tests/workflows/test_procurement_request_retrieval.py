from unittest.mock import AsyncMock

from app.retrieval.generation import RetrievalBudget, RetrievalLevel
from app.workflows.procurement_request import (
    _ProcurementProgressCapture,
    _bound_procurement_inputs,
)
from tests.conftest import run_async


def test_final_procurement_inputs_share_one_global_budget() -> None:
    project_evidence = [
        {
            "document_id": "project-document",
            "chunk_id": "project-chunk",
            "filename": "brief.md",
            "relative_path": "project/brief.md",
            "page_or_section": "Scope",
            "snippet": "project " * 20,
            "score": 1.0,
        },
        {
            "document_id": "overflow-document",
            "chunk_id": "overflow-chunk",
            "filename": "overflow.md",
            "relative_path": "project/overflow.md",
            "page_or_section": "Scope",
            "snippet": "overflow " * 20,
            "score": 0.5,
        },
    ]
    platform_knowledge = [
        {
            "path": "seed/procurement.md",
            "title": "Procurement guidance",
            "section": "Route",
            "snippet": "guidance " * 20,
            "score": 1.0,
        }
    ]
    retriever = AsyncMock()

    bounded_project, bounded_platform, stats = run_async(
        _bound_procurement_inputs(
            retriever,
            project_evidence=project_evidence,
            platform_knowledge=platform_knowledge,
            level=RetrievalLevel.TARGETED_PROJECT,
            budget=RetrievalBudget(
                max_searches=1,
                max_chunks=2,
                max_documents=2,
                max_chars=1_000,
                max_tokens=100,
                max_concurrency=1,
            ),
        )
    )

    assert stats.selected_tokens <= 100
    assert stats.selected_chars <= 1_000
    assert stats.selected_chunks <= 2
    assert stats.selected_documents <= 2
    assert len(bounded_project) == 1
    assert len(bounded_platform) == 1
    assert sum(
        len(item["snippet"]) for item in [*bounded_project, *bounded_platform]
    ) <= 1_000
    retriever.retrieve.assert_not_awaited()


def test_procurement_progress_capture_totals_consistency_calls_across_retries() -> None:
    published: list[dict[str, object]] = []

    async def publish(progress: dict[str, object]) -> None:
        published.append(progress)

    capture = _ProcurementProgressCapture(publish)
    run_async(capture.publish({"stage": "consistency_complete", "ai_call_count": 1}))
    run_async(capture.publish({"stage": "validation_started"}))
    run_async(capture.publish({"stage": "consistency_complete", "ai_call_count": 0}))

    assert capture.consistency_ai_call_count == 1
    assert [item["stage"] for item in published] == [
        "consistency_complete",
        "validation_started",
        "consistency_complete",
    ]
