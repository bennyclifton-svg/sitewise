from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.cost_plan.invoice_candidates import InvoiceCandidate
from app.cost_plan.invoice_service import InvoiceBookingResult
from app.cost_plan.schemas import (
    CostPlanState,
    DependencySnapshot,
    ExtractedInvoice,
    InvoiceAllocationInput,
    InvoiceLineInput,
)
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.schemas.project_snapshot import ProjectSnapshot
from app.workflows.process_invoices import process_invoices
from tests.conftest import run_async


PROJECT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
RUN_ID = uuid.uuid4()
SOURCE_ID = uuid.uuid4()


def _project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="kavanagh",
        title="Kavanagh Residence",
        workspace_path="projects/kavanagh",
        phase="construction",
        status="active",
    )


def _snapshot() -> ProjectSnapshot:
    return ProjectSnapshot.model_validate(
        {
            "schema_version": 1,
            "generated_at": "2026-08-04T00:00:00Z",
            "content_fingerprint": "a" * 64,
            "identity": {
                "project_id": PROJECT_ID,
                "title": "Kavanagh Residence",
                "slug": "kavanagh",
                "workspace_path": "projects/kavanagh",
                "phase": "construction",
                "status": "active",
                "site_address": {"status": "needs_input"},
                "client": {"status": "needs_input"},
            },
            "profile": {
                "project_id": PROJECT_ID,
                "profile_revision": 1,
                "building_class": "class-1a",
                "work_type": "new",
                "subclasses": ["detached-house"],
                "scale": {},
                "complexity": {},
                "work_scope": [],
                "user_role": "architect-pm",
                "state": "NSW",
            },
            "decisions": {"set_revision": 1, "items": []},
            "evidence": {
                "fingerprint": "b" * 64,
                "active_count": 1,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {},
            "open_profile_proposals": [],
        }
    )


def _candidate() -> InvoiceCandidate:
    return InvoiceCandidate(
        source_document_id=SOURCE_ID,
        workspace_file_id=None,
        filename="11-tax-invoice-quoin-architecture-01.md",
        relative_path="projects/kavanagh/_inbox/11-tax-invoice-quoin-architecture-01.md",
        content_hash="c" * 64,
        content="# TAX INVOICE",
    )


def _extracted() -> ExtractedInvoice:
    return ExtractedInvoice(
        supplier_name="Quoin Architecture Pty Ltd",
        invoice_number="QUA-2601",
        invoice_date=date(2026, 3, 18),
        due_date=date(2026, 4, 1),
        related_reference="QUA-KAV-2601",
        subtotal_ex_gst="24000.00",
        gst="2400.00",
        total_including_gst="26400.00",
        lines=[
            InvoiceLineInput(
                description="Stage 1 — Schematic Design, completed",
                amount_ex_gst="24000.00",
            )
        ],
    )


def _allocation() -> InvoiceAllocationInput:
    return InvoiceAllocationInput(
        line_number=1,
        description="Stage 1 — Schematic Design, completed",
        amount_ex_gst="24000.00",
        gst_treatment="taxable",
        cost_item_key="architect",
        cost_item_label="Architect / PM",
        mapping_method="related_reference",
        mapping_confidence="1",
        review_status="mapped",
    )


def _published_state(draft_id: uuid.UUID) -> CostPlanState:
    return CostPlanState(
        project_id=PROJECT_ID,
        artefact_revision_id=draft_id,
        version=6,
        dependency_snapshot=DependencySnapshot(
            profile_revision=1,
            evidence_fingerprint="b" * 64,
            decision_set_revision=1,
            runtime_version="test",
        ),
        items=[],
    )


def test_process_invoices_books_and_publishes_one_cost_plan_version() -> None:
    allocation_id = uuid.uuid4()
    invoice = SimpleNamespace(
        id=uuid.uuid4(),
        allocations=[SimpleNamespace(id=allocation_id)],
    )
    draft_id = uuid.uuid4()
    draft = DraftArtifact(
        id=draft_id,
        project_id=PROJECT_ID,
        workflow_type="create_cost_plan",
        version=6,
        status="draft",
        title="Cost Plan",
        workspace_path="projects/kavanagh/01-cost/cost_plan_v06.md",
        author_user_id=USER_ID,
        content_markdown="# Cost Plan",
        runtime="test",
    )
    session = AsyncMock()
    memory_result = MagicMock()
    memory_result.scalars.return_value.all.return_value = [
        SimpleNamespace(
            supplier_key="quoinarchitectureptyltd",
            description_key="stage 1 schematic design completed",
            cost_item_key="architect",
            cost_item_label="Architect / PM",
        )
    ]
    session.execute.return_value = memory_result
    session.get.return_value = draft
    progress = AsyncMock()

    with (
        patch(
            "app.workflows.process_invoices.count_pending_invoice_ingests",
            new=AsyncMock(return_value=2),
        ),
        patch(
            "app.workflows.process_invoices.discover_invoice_candidates",
            new=AsyncMock(return_value=[_candidate()]),
        ),
        patch(
            "app.workflows.process_invoices._cost_plan_for_mapping",
            new=AsyncMock(return_value=SimpleNamespace(items=[])),
        ),
        patch(
            "app.workflows.process_invoices.extract_invoice",
            return_value=_extracted(),
        ),
        patch(
            "app.workflows.process_invoices.map_invoice_allocations",
            return_value=[_allocation()],
        ) as map_allocations,
        patch(
            "app.workflows.process_invoices.book_invoice",
            new=AsyncMock(
                return_value=InvoiceBookingResult(status="booked", invoice=invoice)
            ),
        ) as book,
        patch(
            "app.workflows.process_invoices.republish_cost_plan_for_ledger",
            new=AsyncMock(return_value=_published_state(draft_id)),
        ) as publish,
        patch(
            "app.workflows.process_invoices.sync_cost_plan_revision_artifacts",
            new=AsyncMock(
                return_value={
                    "workspace_path": "projects/kavanagh/01-cost/Cost_Plan_v06.draft.xlsx"
                }
            ),
        ) as sync,
    ):
        result = run_async(
            process_invoices(
                session,
                project=_project(),
                user_id=USER_ID,
                workflow_run_id=RUN_ID,
                expected_cost_plan_version=5,
                snapshot=_snapshot(),
                progress=progress,
            )
        )

    assert result.booked_invoice_count == 1
    assert result.pending_ingest_count == 2
    assert result.register_row_count == 1
    assert result.cost_plan_version == 6
    assert result.draft_id == draft_id
    assert result.workbook_path.endswith("Cost_Plan_v06.draft.xlsx")
    session.execute.assert_awaited_once()
    assert map_allocations.call_args.kwargs["remembered_mappings"] == {
        (
            "quoinarchitectureptyltd",
            "stage 1 schematic design completed",
        ): ("architect", "Architect / PM")
    }
    assert book.await_args.kwargs["first_published_cost_plan_version"] == 6
    assert publish.await_args.kwargs["expected_base_version"] == 5
    assert sync.await_args.kwargs["provenance_updates"] == {
        "invoice_processing": {
            "workflow_run_id": str(RUN_ID),
            "booked_invoice_ids": [str(invoice.id)],
            "changed_allocation_ids": [str(allocation_id)],
        }
    }
    progress.assert_any_await("complete", 100)


def test_process_invoices_duplicate_only_is_a_noop() -> None:
    session = AsyncMock()
    memory_result = MagicMock()
    memory_result.scalars.return_value.all.return_value = []
    session.execute.return_value = memory_result
    with (
        patch(
            "app.workflows.process_invoices.count_pending_invoice_ingests",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.workflows.process_invoices.discover_invoice_candidates",
            new=AsyncMock(return_value=[_candidate()]),
        ),
        patch(
            "app.workflows.process_invoices._cost_plan_for_mapping",
            new=AsyncMock(return_value=SimpleNamespace(items=[])),
        ),
        patch(
            "app.workflows.process_invoices.extract_invoice",
            return_value=_extracted(),
        ),
        patch(
            "app.workflows.process_invoices.map_invoice_allocations",
            return_value=[_allocation()],
        ),
        patch(
            "app.workflows.process_invoices.book_invoice",
            new=AsyncMock(
                return_value=InvoiceBookingResult(
                    status="duplicate", invoice=SimpleNamespace(id=uuid.uuid4())
                )
            ),
        ),
        patch(
            "app.workflows.process_invoices.republish_cost_plan_for_ledger",
            new=AsyncMock(),
        ) as publish,
    ):
        result = run_async(
            process_invoices(
                session,
                project=_project(),
                user_id=USER_ID,
                workflow_run_id=RUN_ID,
                expected_cost_plan_version=5,
                snapshot=_snapshot(),
            )
        )

    assert result.duplicate_count == 1
    assert result.booked_invoice_count == 0
    assert result.cost_plan_version == 5
    publish.assert_not_awaited()


def test_process_invoices_fails_when_explicit_ids_do_not_resolve() -> None:
    session = AsyncMock()
    with (
        patch(
            "app.workflows.process_invoices.count_pending_invoice_ingests",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.workflows.process_invoices.resolve_invoice_source_document_ids",
            new=AsyncMock(return_value=([], [SOURCE_ID])),
        ),
        patch(
            "app.workflows.process_invoices.discover_invoice_candidates",
            new=AsyncMock(),
        ) as discover,
    ):
        try:
            run_async(
                process_invoices(
                    session,
                    project=_project(),
                    user_id=USER_ID,
                    workflow_run_id=RUN_ID,
                    expected_cost_plan_version=5,
                    snapshot=_snapshot(),
                    source_document_ids=[SOURCE_ID],
                )
            )
            raise AssertionError("expected ValueError")
        except ValueError as exc:
            assert "No matching invoice source documents" in str(exc)
    discover.assert_not_awaited()
