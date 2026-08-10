from __future__ import annotations

import os
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.cost_plan.invoice_candidates import InvoiceCandidate
from app.cost_plan.invoice_service import update_invoice_allocation
from app.cost_plan.models import CostInvoice, CostInvoiceMappingMemory
from app.cost_plan.schemas import (
    CostItemInput,
    CostPlanState,
    DependencySnapshot,
    ExtractedInvoice,
    InvoiceLineInput,
)
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.database.user import User
from app.database.workflow_run import WorkflowRun
from app.workflows.process_invoices import process_invoices
from tests.conftest import run_async


def _candidate(*, invoice_number: int) -> InvoiceCandidate:
    return InvoiceCandidate(
        source_document_id=None,  # type: ignore[arg-type]
        workspace_file_id=None,
        filename=f"invoice-{invoice_number}.md",
        relative_path=f"projects/mapping-memory/_inbox/invoice-{invoice_number}.md",
        content_hash=str(invoice_number) * 64,
        content="# TAX INVOICE",
    )


def _invoice(*, invoice_number: int) -> ExtractedInvoice:
    amount = "100.00" if invoice_number == 1 else "150.00"
    gst = "10.00" if invoice_number == 1 else "15.00"
    total = "110.00" if invoice_number == 1 else "165.00"
    return ExtractedInvoice(
        supplier_name="Example Consulting Pty Ltd",
        invoice_number=f"EX-{invoice_number}",
        invoice_date=date(2026, 8, invoice_number),
        subtotal_ex_gst=amount,
        gst=gst,
        total_including_gst=total,
        lines=[
            InvoiceLineInput(
                description="Retainer reconciliation",
                amount_ex_gst=amount,
            )
        ],
    )


def _mapping_state(*, project_id: uuid.UUID, version: int) -> CostPlanState:
    return CostPlanState(
        project_id=project_id,
        version=version,
        dependency_snapshot=DependencySnapshot(
            profile_revision=1,
            evidence_fingerprint="e" * 64,
            decision_set_revision=1,
            runtime_version="test",
        ),
        items=[
            CostItemInput(
                item_key="consulting",
                cost_code="1",
                category="Consultants",
                item="Professional services",
                budget="1000.00",
                forecast="1000.00",
                basis="Integration fixture",
            )
        ],
    )


def _workflow_run(
    *, run_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID, key: str
) -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        project_id=project_id,
        requested_by_user_id=user_id,
        workflow_type="process_invoices",
        run_brief={},
        idempotency_key=key,
        canonical_request_hash=key * 64,
        frozen_profile_revision=1,
        frozen_snapshot_fingerprint="s" * 64,
        frozen_evidence_fingerprint="e" * 64,
        frozen_decision_set_revision=1,
    )


@pytest.mark.integration
def test_manual_correction_is_remembered_by_the_next_invoice() -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if os.environ.get("ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1" or not database_url:
        pytest.skip("requires an explicitly opted-in disposable PostgreSQL database")
    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    async def exercise() -> None:
        engine = create_async_engine(async_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id, project_id = uuid.uuid4(), uuid.uuid4()
        run_ids = [uuid.uuid4(), uuid.uuid4()]
        draft_ids = [uuid.uuid4(), uuid.uuid4()]
        try:
            async with factory() as session:
                project = Project(
                    id=project_id,
                    owner_user_id=user_id,
                    slug=f"mapping-memory-{project_id}",
                    title="Invoice mapping memory",
                    workspace_path=f"projects/{project_id}",
                    phase="construction",
                    status="active",
                )
                session.add(
                    User(id=user_id, email=f"mapping-memory-{user_id}@example.com")
                )
                session.add(project)
                session.add_all(
                    [
                        DraftArtifact(
                            id=draft_ids[index],
                            project_id=project_id,
                            workflow_type="create_cost_plan",
                            version=index + 2,
                            status="draft",
                            title="Cost Plan",
                            workspace_path=(
                                f"projects/{project_id}/cost-plan-v{index + 2}.md"
                            ),
                            author_user_id=user_id,
                            content_markdown="# Cost Plan",
                            runtime="test",
                        )
                        for index in range(2)
                    ]
                )
                session.add_all(
                    [
                        _workflow_run(
                            run_id=run_ids[index],
                            project_id=project_id,
                            user_id=user_id,
                            key=str(index + 1),
                        )
                        for index in range(2)
                    ]
                )
                await session.flush()

                async def process(
                    *, invoice_number: int, expected_version: int
                ) -> None:
                    mapping_state = _mapping_state(
                        project_id=project_id,
                        version=expected_version,
                    )
                    published_state = mapping_state.model_copy(
                        update={
                            "artefact_revision_id": draft_ids[invoice_number - 1],
                            "version": expected_version + 1,
                        }
                    )
                    with (
                        patch(
                            "app.workflows.process_invoices.count_pending_invoice_ingests",
                            new=AsyncMock(return_value=0),
                        ),
                        patch(
                            "app.workflows.process_invoices.discover_invoice_candidates",
                            new=AsyncMock(
                                return_value=[_candidate(invoice_number=invoice_number)]
                            ),
                        ),
                        patch(
                            "app.workflows.process_invoices._cost_plan_for_mapping",
                            new=AsyncMock(return_value=mapping_state),
                        ),
                        patch(
                            "app.workflows.process_invoices.extract_invoice",
                            return_value=_invoice(invoice_number=invoice_number),
                        ),
                        patch(
                            "app.workflows.process_invoices.republish_cost_plan_for_ledger",
                            new=AsyncMock(return_value=published_state),
                        ),
                        patch(
                            "app.workflows.process_invoices.sync_cost_plan_revision_artifacts",
                            new=AsyncMock(
                                return_value={
                                    "workspace_path": f"cost-plan-v{expected_version + 1}.xlsx"
                                }
                            ),
                        ),
                        patch(
                            "app.workflows.process_invoices.dependency_snapshot",
                            return_value=SimpleNamespace(),
                        ),
                    ):
                        result = await process_invoices(
                            session,
                            project=project,
                            user_id=user_id,
                            workflow_run_id=run_ids[invoice_number - 1],
                            expected_cost_plan_version=expected_version,
                            snapshot=SimpleNamespace(),  # type: ignore[arg-type]
                        )
                    assert result.booked_invoice_count == 1

                await process(invoice_number=1, expected_version=1)
                first = (
                    await session.execute(
                        select(CostInvoice)
                        .where(
                            CostInvoice.project_id == project_id,
                            CostInvoice.invoice_key == "ex1",
                        )
                        .options(selectinload(CostInvoice.allocations))
                    )
                ).scalar_one()
                assert first.allocations[0].review_status == "needs_review"

                await update_invoice_allocation(
                    session,
                    project_id=project_id,
                    user_id=user_id,
                    allocation_id=first.allocations[0].id,
                    expected_revision=1,
                    cost_item_key="temporary",
                    cost_item_label="Temporary mapping",
                )
                await update_invoice_allocation(
                    session,
                    project_id=project_id,
                    user_id=user_id,
                    allocation_id=first.allocations[0].id,
                    expected_revision=2,
                    cost_item_key="consulting",
                    cost_item_label="Professional services",
                )
                memory_count = await session.scalar(
                    select(func.count())
                    .select_from(CostInvoiceMappingMemory)
                    .where(CostInvoiceMappingMemory.project_id == project_id)
                )
                assert memory_count == 1

                await process(invoice_number=2, expected_version=2)
                second = (
                    await session.execute(
                        select(CostInvoice)
                        .where(
                            CostInvoice.project_id == project_id,
                            CostInvoice.invoice_key == "ex2",
                        )
                        .options(selectinload(CostInvoice.allocations))
                    )
                ).scalar_one()
                allocation = second.allocations[0]
                assert allocation.cost_item_key == "consulting"
                assert allocation.cost_item_label == "Professional services"
                assert allocation.mapping_method == "remembered"
                assert allocation.review_status == "mapped"
                await session.rollback()
        finally:
            await engine.dispose()

    run_async(exercise())
