from __future__ import annotations

import hashlib
import json
import mimetypes
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.database.project import Project
from app.database.project_document_selection import ProjectDocumentSelection
from app.projects.document_selections import lock_workflow_inputs
from tender.models import TenderComparison, TenderDocument, TenderQuote
from tender.schemas import ComparisonDetail, TenderIntakeRequest, TenderIntakeResponse
from tender.services import jobs
from tender.services.project_context_adapter import (
    ContextRevisionConflict,
    ContextValidationError,
    ProjectContextAdapter,
)


class TenderIntakeNotReady(ValueError):
    def __init__(self, missing: list[str], unsupported: list[str]) -> None:
        self.missing = missing
        self.unsupported = unsupported
        super().__init__("Tender intake is not ready")


class TenderIdempotencyConflict(ValueError):
    pass


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


async def create_immutable_intake(
    session: AsyncSession,
    *,
    request: TenderIntakeRequest,
    owner_user_id: uuid.UUID,
    adapter: ProjectContextAdapter | None = None,
) -> TenderIntakeResponse:
    project_result = await session.execute(
        select(Project).where(Project.id == request.project_id, Project.owner_user_id == owner_user_id).with_for_update()
    )
    project = project_result.scalar_one_or_none()
    if project is None:
        raise ContextValidationError("Project not found")
    idempotency_key = _digest({"project_id": str(project.id), "workflow_type": "tender_comparison", "turn_id": request.turn_id})
    request_fingerprint = _digest({
        "project_id": str(project.id),
        "workflow_type": "tender_comparison",
        "expected_profile_revision": request.expected_profile_revision,
        "expected_selection_revision": request.expected_selection_revision,
        "context_overrides": request.context_overrides,
    })
    existing_result = await session.execute(
        select(TenderComparison).where(
            TenderComparison.project_id == project.id,
            TenderComparison.idempotency_key == idempotency_key,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        if existing.context_provenance.get("request_fingerprint") != request_fingerprint:
            raise TenderIdempotencyConflict("turn_id was already used with different Tender inputs")
        from tender.router import get_comparison_detail
        detail = await get_comparison_detail(session, existing.id)
        if detail is None:
            raise ContextValidationError("Existing comparison is unavailable")
        return TenderIntakeResponse(comparison=ComparisonDetail.model_validate(detail), idempotent_replay=True)
    selection_result = await session.execute(
        select(ProjectDocumentSelection).where(
            ProjectDocumentSelection.project_id == project.id,
            ProjectDocumentSelection.purpose == "tender_comparison",
        ).with_for_update()
    )
    selection_row = selection_result.scalar_one_or_none()
    current_selection_revision = selection_row.revision if selection_row is not None else 0
    if current_selection_revision != request.expected_selection_revision:
        raise ContextRevisionConflict("selection", request.expected_selection_revision, current_selection_revision)

    prepared = await (adapter or ProjectContextAdapter()).prepare(
        session,
        project_id=project.id,
        owner_user_id=owner_user_id,
        expected_profile_revision=request.expected_profile_revision,
        expected_selection_revision=request.expected_selection_revision,
        overrides=request.context_overrides,
    )
    if not prepared.ready or prepared.context is None:
        raise TenderIntakeNotReady(prepared.missing_fields, prepared.unsupported_reasons)

    input_payload = {
        "context": prepared.context.model_dump(mode="json"),
        "provenance": prepared.provenance.model_dump(mode="json"),
    }
    input_fingerprint = _digest(input_payload)

    from app.projects.document_selections import read_selection
    selection = await read_selection(session, project_id=project.id, revision=request.expected_selection_revision)
    stored_provenance = prepared.provenance.model_dump(mode="json")
    stored_provenance["request_fingerprint"] = request_fingerprint
    comparison = TenderComparison(
        project_id=project.id,
        context=prepared.context.model_dump(mode="json"),
        context_provenance=stored_provenance,
        input_fingerprint=input_fingerprint,
        idempotency_key=idempotency_key,
        created_by=owner_user_id,
    )
    session.add(comparison)
    await session.flush()

    quote_rows: list[TenderQuote] = []
    locked_file_ids: list[uuid.UUID] = []
    for group in selection.quote_groups:
        quote = TenderQuote(comparison_id=comparison.id, builder_name=group.builder_name)
        session.add(quote)
        await session.flush()
        set_committed_value(quote, "comparison", comparison)
        document_rows: list[TenderDocument] = []
        for file in group.files:
            document = TenderDocument(
                quote_id=quote.id,
                storage_path=file.storage_key,
                original_filename=file.filename,
                mime_type=mimetypes.guess_type(file.filename)[0] or "application/octet-stream",
                ingest_status="pending",
                content_hash=file.content_hash,
                workspace_file_id=file.workspace_file_id,
                storage_bucket=file.storage_bucket,
                storage_version=file.content_hash,
                quote_group_position=group.position,
                input_position=file.position,
            )
            session.add(document)
            await session.flush()
            await jobs.enqueue(
                session,
                kind="ingest_document",
                comparison_id=comparison.id,
                quote_id=quote.id,
                payload={"document_id": str(document.id)},
            )
            document_rows.append(document)
            locked_file_ids.append(file.workspace_file_id)
        set_committed_value(quote, "documents", document_rows)
        quote_rows.append(quote)
    set_committed_value(comparison, "quotes", quote_rows)
    await lock_workflow_inputs(
        session,
        project_id=project.id,
        workflow_type="tender_comparison",
        workflow_id=comparison.id,
        workspace_file_ids=locked_file_ids,
    )
    return TenderIntakeResponse(comparison=ComparisonDetail.model_validate(comparison))
