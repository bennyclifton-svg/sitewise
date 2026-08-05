from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.api.projects import _apply_invoice_statuses, _pending_invoice_status
from app.schemas.projects import EvidencePreview
from tests.conftest import run_async


def _preview(document_id: uuid.UUID, filename: str = "structural-invoice.md"):
    return EvidencePreview(
        id=document_id,
        title="Structural invoice",
        filename=filename,
        relative_path=f"projects/kavanagh/_inbox/{filename}",
        source_type="project_evidence",
        document_class="project_evidence",
        excerpt="# TAX INVOICE\n\n**Invoice number:** CST-2601",
    )


def _session(*, invoices: list, briefs: list[dict]) -> AsyncMock:
    invoice_result = MagicMock()
    invoice_result.all.return_value = invoices
    run_result = MagicMock()
    run_result.scalars.return_value.all.return_value = briefs
    session = AsyncMock()
    session.execute.side_effect = [invoice_result, run_result]
    return session


def test_invoice_registry_marks_selected_active_invoice_as_processing() -> None:
    document_id = uuid.uuid4()
    preview = _preview(document_id)

    result = run_async(
        _apply_invoice_statuses(
            _session(
                invoices=[],
                briefs=[
                    {"parameters": {"source_document_ids": [str(document_id)]}}
                ],
            ),
            project_id=uuid.uuid4(),
            previews=[preview],
        )
    )

    assert result[0].invoice_status == "processing"


def test_booked_or_review_state_takes_precedence_over_active_run() -> None:
    document_id = uuid.uuid4()
    preview = _preview(document_id)
    invoice = SimpleNamespace(
        source_document_id=document_id,
        workspace_file_id=None,
        processing_status="needs_review",
    )

    result = run_async(
        _apply_invoice_statuses(
            _session(invoices=[invoice], briefs=[{"parameters": {}}]),
            project_id=uuid.uuid4(),
            previews=[preview],
        )
    )

    assert result[0].invoice_status == "needs_review"


def test_ingest_status_exposes_reading_and_failure_before_indexing() -> None:
    assert (
        _pending_invoice_status(
            SimpleNamespace(filename="invoice.pdf", ingest_status="ingesting")
        )
        == "reading"
    )
    assert (
        _pending_invoice_status(
            SimpleNamespace(filename="invoice.pdf", ingest_status="failed")
        )
        == "failed"
    )
    assert (
        _pending_invoice_status(
            SimpleNamespace(filename="owner-brief.pdf", ingest_status="ingesting")
        )
        is None
    )
