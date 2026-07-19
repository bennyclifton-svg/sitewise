"""Hosted Sort Files: classify inbox entries, move storage, re-ingest, build manifest."""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.document_chunk import DocumentChunk
from app.database.project import Project
from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile
from app.database.workspace_files import (
    get_workspace_file_by_path,
    list_workspace_files_under_prefix,
    upsert_workspace_file,
)
from app.inbox.paths import build_storage_key
from app.intake.classifier import classify_inbox_destination, is_intake_manifest
from app.storage.project_files import download_project_file, move_project_file
from ingest.document_metadata import parse_document_metadata
from ingest.hosted import ingest_hosted_file, source_document_id_for_path
from ingest.ids import document_id

SortOutcome = Literal["moved", "already-filed", "unresolved", "skipped", "refused"]

_MANIFEST_VERSION_PATTERN = re.compile(r"intake_manifest_v(\d+)\.md$", re.I)


@dataclass(frozen=True, slots=True)
class SortFileRecord:
    source_path: str
    filename: str
    outcome: SortOutcome
    destination_path: str | None = None
    destination_filename: str | None = None
    reason: str | None = None
    document_number: str | None = None
    title: str | None = None
    revision: str | None = None
    category: str | None = None


@dataclass
class SortFilesCounts:
    inspected: int = 0
    moved: int = 0
    already_filed: int = 0
    unresolved: int = 0
    skipped: int = 0
    refused: int = 0


@dataclass
class SortFilesResult:
    records: list[SortFileRecord] = field(default_factory=list)
    counts: SortFilesCounts = field(default_factory=SortFilesCounts)
    warnings: list[str] = field(default_factory=list)
    manifest_version: int = 1
    manifest_workspace_path: str = ""
    manifest_markdown: str = ""


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return f".{filename.rsplit('.', maxsplit=1)[-1].lower()}"


_PREVIEW_BYTE_LIMIT = 4096


async def _classification_preview(record: WorkspaceFile) -> str | None:
    extension = _extension(record.filename)
    if extension not in {".md", ".txt", ".pdf", ".docx"}:
        return None
    try:
        content = await asyncio.to_thread(
            download_project_file,
            storage_key=record.storage_key,
        )
    except Exception:
        return None
    if extension == ".pdf":
        try:
            from app.inbox.pdf_inspect import inspect_pdf

            info = inspect_pdf(content)
        except Exception:
            return None
        if info.encrypted or not info.pages:
            return None
        text = info.pages[0].text.strip()
        return text[:_PREVIEW_BYTE_LIMIT] if text else None
    return content[:_PREVIEW_BYTE_LIMIT].decode("utf-8", errors="replace")


def _inbox_prefix(project: Project) -> str:
    return f"{project.workspace_path.rstrip('/')}/_inbox"


def _destination_workspace_path(
    project: Project,
    destination_folder: str,
    filename: str,
) -> str:
    return f"{project.workspace_path.rstrip('/')}/{destination_folder.strip('/')}/{filename}"


def _next_manifest_version(files: list[WorkspaceFile], drafts_version: int) -> int:
    versions = [drafts_version]
    for record in files:
        match = _MANIFEST_VERSION_PATTERN.search(record.filename)
        if match:
            versions.append(int(match.group(1)))
    return max(versions, default=0) + 1


def _purge_source_document(
    relative_path: str,
    project_id: uuid.UUID,
    source_document_id: uuid.UUID | None = None,
) -> None:
    from ingest.db import get_sync_session_factory

    candidate_ids = {
        document_id(relative_path),
        document_id(relative_path, project_id=project_id),
    }
    if source_document_id is not None:
        candidate_ids.add(source_document_id)
    candidate_id_values = tuple(candidate_ids)

    factory = get_sync_session_factory()
    with factory() as session:
        stale_ids = set(
            session.scalars(
                select(SourceDocument.id).where(
                    SourceDocument.project_id == project_id,
                    or_(
                        SourceDocument.id.in_(candidate_id_values),
                        SourceDocument.relative_path == relative_path,
                    )
                )
            )
        )
        if stale_ids:
            stale_id_values = tuple(stale_ids)
            session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id.in_(stale_id_values))
            )
            session.execute(
                delete(SourceDocument).where(SourceDocument.id.in_(stale_id_values))
            )
        session.commit()


def _build_manifest_markdown(
    *,
    project: Project,
    run_at: datetime,
    version: int,
    result: SortFilesResult,
) -> str:
    inbox_path = _inbox_prefix(project)
    lines = [
        "---",
        "status: draft",
        "author: agent",
        f"run_at: {run_at.isoformat()}",
        f"project_path: {project.workspace_path}",
        f"inbox_path: {inbox_path}",
        f"inspected: {result.counts.inspected}",
        f"moved: {result.counts.moved}",
        f"already_filed: {result.counts.already_filed}",
        f"unresolved: {result.counts.unresolved}",
        f"skipped: {result.counts.skipped}",
        f"refused: {result.counts.refused}",
        "---",
        "",
        f"# Intake manifest v{version:02d}",
        "",
        "## Summary",
        "",
        f"- Inspected: {result.counts.inspected}",
        f"- Moved: {result.counts.moved}",
        f"- Already filed: {result.counts.already_filed}",
        f"- Unresolved: {result.counts.unresolved}",
        f"- Skipped: {result.counts.skipped}",
        f"- Refused: {result.counts.refused}",
        "",
    ]

    for section, outcome in (
        ("Moved", "moved"),
        ("Already filed", "already-filed"),
        ("Unresolved", "unresolved"),
        ("Skipped", "skipped"),
        ("Refused", "refused"),
    ):
        rows = [record for record in result.records if record.outcome == outcome]
        lines.append(f"## {section}")
        lines.append("")
        if not rows:
            lines.append("_None._")
        else:
            for record in rows:
                destination = record.destination_path or "—"
                lines.append(f"- `{record.source_path}` → `{destination}` ({record.reason or outcome})")
        lines.append("")

    if result.warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in result.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


async def _resolve_destination_filename(
    *,
    source_path: str,
    destination_folder: str,
    filename: str,
    project: Project,
    preview_snippet: str | None = None,
) -> str:
    filed_path = _destination_workspace_path(project, destination_folder, filename)
    parsed = parse_document_metadata(
        file_name=filename,
        filed_path=filed_path,
        source_path=source_path,
        preview_snippet=preview_snippet,
    )
    if parsed.confidence == "low":
        return filename
    return parsed.canonical_file_name


async def _move_workspace_file(
    session: AsyncSession,
    *,
    project: Project,
    record: WorkspaceFile,
    destination_workspace_path: str,
    destination_filename: str,
) -> WorkspaceFile:
    if destination_workspace_path.endswith("/"):
        destination_workspace_path = destination_workspace_path.rstrip("/")
    if not destination_workspace_path.endswith(destination_filename):
        folder = destination_workspace_path.rsplit("/", maxsplit=1)[0]
        destination_workspace_path = f"{folder}/{destination_filename}"

    content = await asyncio.to_thread(
        download_project_file,
        storage_key=record.storage_key,
    )
    destination_key = build_storage_key(str(project.id), destination_workspace_path)

    await asyncio.to_thread(
        move_project_file,
        source_key=record.storage_key,
        destination_key=destination_key,
        content=content,
        filename=destination_filename,
    )

    if record.source_document_id is not None or record.workspace_path:
        await asyncio.to_thread(
            _purge_source_document,
            record.workspace_path,
            project.id,
            record.source_document_id,
        )

    extension = _extension(destination_filename)
    ingested = await asyncio.to_thread(
        ingest_hosted_file,
        content=content,
        workspace_path=destination_workspace_path,
        project_id=project.id,
        project_slug=project.slug,
        project_phase=project.phase,
        filename=destination_filename,
        extension=extension,
        skip_if_unchanged=False,
    )
    ingest_status = "ingested" if ingested else "skipped"
    source_doc_id = await asyncio.to_thread(
        source_document_id_for_path,
        destination_workspace_path,
        project_id=project.id,
    )

    moved = await upsert_workspace_file(
        session,
        project_id=project.id,
        workspace_path=destination_workspace_path,
        filename=destination_filename,
        storage_bucket=record.storage_bucket,
        storage_key=destination_key,
        content_hash=record.content_hash,
        size_bytes=record.size_bytes,
        ingest_status=ingest_status,
        ingest_error=None,
        source_document_id=source_doc_id,
    )

    await session.delete(record)
    await session.flush()
    return moved


async def sort_inbox_files(
    session: AsyncSession,
    *,
    project: Project,
    manifest_version_hint: int = 0,
) -> SortFilesResult:
    inbox_prefix = _inbox_prefix(project)
    inbox_files = await list_workspace_files_under_prefix(
        session,
        project_id=project.id,
        path_prefix=inbox_prefix,
    )

    result = SortFilesResult()
    manifest_version = _next_manifest_version(inbox_files, manifest_version_hint)
    run_at = datetime.now(timezone.utc)

    for record in inbox_files:
        if is_intake_manifest(record.filename):
            result.records.append(
                SortFileRecord(
                    source_path=record.workspace_path,
                    filename=record.filename,
                    outcome="skipped",
                    reason="Prior intake manifest",
                )
            )
            result.counts.skipped += 1
            continue

        result.counts.inspected += 1
        preview_snippet = await _classification_preview(record)
        destination_folder = classify_inbox_destination(
            workspace_path=record.workspace_path,
            filename=record.filename,
            project_workspace_path=project.workspace_path,
            preview_snippet=preview_snippet,
        )
        if destination_folder is None:
            result.records.append(
                SortFileRecord(
                    source_path=record.workspace_path,
                    filename=record.filename,
                    outcome="unresolved",
                    reason="No confident lifecycle-folder match",
                )
            )
            result.counts.unresolved += 1
            continue

        destination_filename = await _resolve_destination_filename(
            source_path=record.workspace_path,
            destination_folder=destination_folder,
            filename=record.filename,
            project=project,
            preview_snippet=preview_snippet,
        )
        destination_path = _destination_workspace_path(
            project,
            destination_folder,
            destination_filename,
        )

        if not destination_path.startswith(project.workspace_path.rstrip("/") + "/"):
            result.records.append(
                SortFileRecord(
                    source_path=record.workspace_path,
                    filename=record.filename,
                    outcome="refused",
                    destination_path=destination_path,
                    reason="Move blocked outside active project",
                )
            )
            result.counts.refused += 1
            continue

        existing = await get_workspace_file_by_path(
            session,
            project_id=project.id,
            workspace_path=destination_path,
        )
        if existing is not None:
            if existing.content_hash == record.content_hash:
                metadata = _register_fields_from_path(
                    source_path=record.workspace_path,
                    filed_path=destination_path,
                    filename=record.filename,
                    preview_snippet=preview_snippet,
                )
                result.records.append(
                    SortFileRecord(
                        source_path=record.workspace_path,
                        filename=record.filename,
                        outcome="already-filed",
                        destination_path=destination_path,
                        destination_filename=destination_filename,
                        reason="Destination already contains identical content",
                        **metadata,
                    )
                )
                result.counts.already_filed += 1
                continue

            result.records.append(
                SortFileRecord(
                    source_path=record.workspace_path,
                    filename=record.filename,
                    outcome="refused",
                    destination_path=destination_path,
                    destination_filename=destination_filename,
                    reason="Destination exists with different content",
                )
            )
            result.counts.refused += 1
            continue

        try:
            await _move_workspace_file(
                session,
                project=project,
                record=record,
                destination_workspace_path=destination_path,
                destination_filename=destination_filename,
            )
        except Exception as exc:
            result.records.append(
                SortFileRecord(
                    source_path=record.workspace_path,
                    filename=record.filename,
                    outcome="refused",
                    destination_path=destination_path,
                    destination_filename=destination_filename,
                    reason=f"Move failed: {exc}",
                )
            )
            result.counts.refused += 1
            result.warnings.append(f"Failed to move {record.filename}: {exc}")
            continue

        metadata = _register_fields_from_path(
            source_path=record.workspace_path,
            filed_path=destination_path,
            filename=destination_filename,
            preview_snippet=preview_snippet,
        )
        result.records.append(
            SortFileRecord(
                source_path=record.workspace_path,
                filename=record.filename,
                outcome="moved",
                destination_path=destination_path,
                destination_filename=destination_filename,
                reason="Classified and filed",
                **metadata,
            )
        )
        result.counts.moved += 1

    result.manifest_version = manifest_version
    result.manifest_workspace_path = (
        f"{inbox_prefix}/intake_manifest_v{manifest_version:02d}.md"
    )
    result.manifest_markdown = _build_manifest_markdown(
        project=project,
        run_at=run_at,
        version=manifest_version,
        result=result,
    )
    return result


def _register_fields_from_path(
    *,
    source_path: str,
    filed_path: str,
    filename: str,
    preview_snippet: str | None = None,
) -> dict[str, str | None]:
    parsed = parse_document_metadata(
        file_name=filename,
        filed_path=filed_path,
        source_path=source_path,
        preview_snippet=preview_snippet,
    )
    return {
        "document_number": parsed.document_number or None,
        "title": parsed.title or None,
        "revision": parsed.revision or None,
        "category": parsed.discipline or None,
    }
