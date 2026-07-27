"""Non-destructive repair preview for already-filed project evidence."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.activity_events import record_activity_events
from app.database.project import Project
from app.database.source_document import SourceDocument
from app.database.workspace_files import (
    get_workspace_file_by_path,
    list_workspace_files_for_project,
)
from app.intake.classifier import classify_inbox_destination, is_intake_manifest
from app.intake.sort_service import (
    _destination_workspace_path,
    _extension,
    _file_previews,
    _move_workspace_file,
)
from app.storage.project_files import download_project_file
from app.schemas.projects import WorkflowTraceEvent
from ingest.document_metadata import parse_document_metadata
from ingest.hosted import ingest_hosted_file, source_document_id_for_path

RepairStatus = Literal["change", "unchanged", "needs_review", "conflict"]


@dataclass(frozen=True, slots=True)
class FileRepairPreview:
    status: RepairStatus
    current_path: str
    current_filename: str
    proposed_path: str
    proposed_filename: str
    document_number: str | None
    title: str | None
    revision: str | None
    category: str | None
    confidence: str
    changes: tuple[str, ...] = ()
    reason: str | None = None


@dataclass(slots=True)
class FileRepairPreviewResult:
    inspected: int = 0
    changes: int = 0
    needs_review: int = 0
    conflicts: int = 0
    unchanged: int = 0
    rows: list[FileRepairPreview] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FileRepairApplyRow:
    current_path: str
    proposed_path: str
    status: Literal["applied", "failed", "skipped"]
    reason: str | None = None


@dataclass(slots=True)
class FileRepairApplyResult:
    applied: int = 0
    failed: int = 0
    skipped: int = 0
    rows: list[FileRepairApplyRow] = field(default_factory=list)


def _current_destination_folder(project: Project, workspace_path: str) -> str:
    prefix = project.workspace_path.rstrip("/") + "/"
    relative = workspace_path.replace("\\", "/")
    if relative.startswith(prefix):
        relative = relative[len(prefix) :]
    return relative.rsplit("/", maxsplit=1)[0]


def _metadata_changes(
    source: SourceDocument | None,
    *,
    document_number: str,
    title: str,
    revision: str,
    discipline: str,
) -> bool:
    metadata = (
        source.document_metadata
        if source is not None and isinstance(source.document_metadata, dict)
        else {}
    )
    expected = {
        "document_number": document_number,
        "title": title,
        "revision": revision,
        "discipline": discipline,
    }
    return any(metadata.get(key) != value for key, value in expected.items())


async def preview_existing_file_repairs(
    session: AsyncSession,
    *,
    project: Project,
) -> FileRepairPreviewResult:
    """Inspect filed evidence and return proposed changes without writing anything."""
    files = await list_workspace_files_for_project(session, project_id=project.id)
    result = FileRepairPreviewResult()
    project_prefix = project.workspace_path.rstrip("/") + "/"

    for record in files:
        path = record.workspace_path.replace("\\", "/")
        if (
            not path.startswith(project_prefix)
            or "/_inbox/" in path
            or is_intake_manifest(record.filename)
            or record.source_document_id is None
        ):
            continue

        result.inspected += 1
        previews = await _file_previews(record)
        destination_folder = classify_inbox_destination(
            workspace_path=record.workspace_path,
            filename=record.filename,
            project_workspace_path=project.workspace_path,
            preview_snippet=previews.classification,
        ) or _current_destination_folder(project, record.workspace_path)
        filed_path = _destination_workspace_path(
            project,
            destination_folder,
            record.filename,
        )
        parsed = parse_document_metadata(
            file_name=record.filename,
            filed_path=filed_path,
            source_path=record.workspace_path,
            preview_snippet=previews.for_identity,
        )
        proposed_filename = (
            parsed.canonical_file_name
            if parsed.confidence != "low"
            else record.filename
        )
        proposed_path = _destination_workspace_path(
            project,
            destination_folder,
            proposed_filename,
        )

        source = await session.get(SourceDocument, record.source_document_id)
        source = source if isinstance(source, SourceDocument) else None
        changes: list[str] = []
        if destination_folder != _current_destination_folder(project, record.workspace_path):
            changes.append("folder")
        if proposed_filename != record.filename:
            changes.append("filename")
        if _metadata_changes(
            source,
            document_number=parsed.document_number,
            title=parsed.title,
            revision=parsed.revision,
            discipline=parsed.discipline,
        ):
            changes.append("metadata")

        status: RepairStatus = "change" if changes else "unchanged"
        reason: str | None = None
        if parsed.confidence == "low":
            status = "needs_review"
            reason = "Document identity could not be read confidently"
        elif proposed_path != record.workspace_path:
            existing = await get_workspace_file_by_path(
                session,
                project_id=project.id,
                workspace_path=proposed_path,
            )
            if existing is not None and existing.id != record.id:
                status = "conflict"
                reason = (
                    "Proposed destination already contains identical content"
                    if existing.content_hash == record.content_hash
                    else "Proposed destination exists with different content"
                )

        row = FileRepairPreview(
            status=status,
            current_path=record.workspace_path,
            current_filename=record.filename,
            proposed_path=proposed_path,
            proposed_filename=proposed_filename,
            document_number=parsed.document_number or None,
            title=parsed.title or None,
            revision=parsed.revision or None,
            category=parsed.discipline or None,
            confidence=parsed.confidence,
            changes=tuple(changes),
            reason=reason,
        )
        result.rows.append(row)
        if status == "change":
            result.changes += 1
        elif status == "needs_review":
            result.needs_review += 1
        elif status == "conflict":
            result.conflicts += 1
        else:
            result.unchanged += 1

    return result


async def _refresh_workspace_file_metadata(
    session: AsyncSession,
    *,
    project: Project,
    record,
) -> None:
    content = await asyncio.to_thread(
        download_project_file,
        storage_key=record.storage_key,
    )
    ingested = await asyncio.to_thread(
        ingest_hosted_file,
        content=content,
        workspace_path=record.workspace_path,
        project_id=project.id,
        project_slug=project.slug,
        project_phase=project.phase,
        filename=record.filename,
        extension=_extension(record.filename),
        skip_if_unchanged=False,
    )
    record.ingest_status = "ingested" if ingested else "skipped"
    record.ingest_error = None
    record.source_document_id = await asyncio.to_thread(
        source_document_id_for_path,
        record.workspace_path,
        project_id=project.id,
    )
    await session.flush()


async def apply_existing_file_repairs(
    session: AsyncSession,
    *,
    project: Project,
    workspace_paths: set[str],
) -> FileRepairApplyResult:
    """Re-check and apply explicitly selected, conflict-free repair proposals."""
    preview = await preview_existing_file_repairs(session, project=project)
    proposals = {row.current_path: row for row in preview.rows}
    result = FileRepairApplyResult()

    for workspace_path in sorted(workspace_paths):
        proposal = proposals.get(workspace_path)
        if proposal is None or proposal.status != "change":
            result.skipped += 1
            result.rows.append(
                FileRepairApplyRow(
                    current_path=workspace_path,
                    proposed_path=proposal.proposed_path if proposal else workspace_path,
                    status="skipped",
                    reason=proposal.reason if proposal else "No current repair proposal",
                )
            )
            continue

        record = await get_workspace_file_by_path(
            session,
            project_id=project.id,
            workspace_path=workspace_path,
        )
        if record is None:
            result.failed += 1
            result.rows.append(
                FileRepairApplyRow(
                    current_path=workspace_path,
                    proposed_path=proposal.proposed_path,
                    status="failed",
                    reason="Source file changed after preview",
                )
            )
            continue

        try:
            if proposal.proposed_path != workspace_path:
                await _move_workspace_file(
                    session,
                    project=project,
                    record=record,
                    destination_workspace_path=proposal.proposed_path,
                    destination_filename=proposal.proposed_filename,
                )
            else:
                await _refresh_workspace_file_metadata(
                    session,
                    project=project,
                    record=record,
                )
        except Exception as exc:
            result.failed += 1
            result.rows.append(
                FileRepairApplyRow(
                    current_path=workspace_path,
                    proposed_path=proposal.proposed_path,
                    status="failed",
                    reason=str(exc),
                )
            )
            continue

        result.applied += 1
        result.rows.append(
            FileRepairApplyRow(
                current_path=workspace_path,
                proposed_path=proposal.proposed_path,
                status="applied",
            )
        )

    activity_status = "failed" if result.failed else "complete"
    await record_activity_events(
        session,
        project_id=project.id,
        source="document_repair",
        run_id=uuid.uuid4(),
        events=[
            WorkflowTraceEvent(
                step="apply",
                status=activity_status,
                message=(
                    f"Existing document repair applied {result.applied}, "
                    f"failed {result.failed}, skipped {result.skipped}."
                ),
                metadata={
                    "selected": len(workspace_paths),
                    "applied": result.applied,
                    "failed": result.failed,
                    "skipped": result.skipped,
                },
            )
        ],
    )
    await session.commit()
    return result
