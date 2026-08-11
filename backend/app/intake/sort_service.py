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
from app.projects.consultant_facts import upsert_consultant_fact_from_document
from app.storage.project_files import (
    delete_project_files,
    download_project_file,
    upload_project_file,
)
from ingest.document_metadata import parse_document_metadata
from ingest.hosted import ingest_hosted_file, source_document_id_for_path
from ingest.ids import document_id
from ingest.title_block import pdf_title_block_preview

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
_TRUSTED_SPLIT_IDENTITY_METHODS = {"drawing_schedule_v1", "title_block_v1"}
_SPLIT_IDENTITY_KEYS = {
    "document_number",
    "drawing_number",
    "revision",
    "sheet_index",
    "sheet_number_label",
    "sheet_scale",
    "sheet_total",
    "title",
}


@dataclass(frozen=True, slots=True)
class _Previews:
    """Two views of one file, because they answer different questions.

    ``classification`` is the broad first-page text used to pick a lifecycle
    folder. ``identity`` is the drawing's title block read by position; a sheet's
    text order cannot be trusted for identity, but the broad text is still the
    better signal for classification.
    """

    classification: str | None = None
    identity: str | None = None

    @property
    def for_identity(self) -> str | None:
        return self.identity or self.classification


async def _file_previews(record: WorkspaceFile) -> _Previews:
    extension = _extension(record.filename)
    if extension not in {".md", ".txt", ".pdf", ".docx"}:
        return _Previews()
    try:
        content = await asyncio.to_thread(
            download_project_file,
            storage_key=record.storage_key,
        )
    except Exception:
        return _Previews()
    if extension == ".pdf":
        identity = await asyncio.to_thread(pdf_title_block_preview, content)
        try:
            from app.inbox.pdf_inspect import inspect_pdf

            info = inspect_pdf(content)
        except Exception:
            return _Previews(identity=identity)
        if info.encrypted or not info.pages:
            return _Previews(identity=identity)
        text = info.pages[0].text.strip()
        return _Previews(
            classification=text[:_PREVIEW_BYTE_LIMIT] if text else None,
            identity=identity,
        )
    return _Previews(
        classification=content[:_PREVIEW_BYTE_LIMIT].decode("utf-8", errors="replace")
    )


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
    document_metadata: dict[str, object] | None = None,
) -> str:
    filed_path = _destination_workspace_path(project, destination_folder, filename)
    parse_filename = filename
    split_method = (document_metadata or {}).get("split_method")
    if split_method in _TRUSTED_SPLIT_IDENTITY_METHODS:
        title = (document_metadata or {}).get("title")
        document_number = (document_metadata or {}).get("document_number")
        revision = (document_metadata or {}).get("revision")
        if isinstance(title, str) and title.strip():
            identity_lines = [f"Drawing Title {title.strip()}"]
            if isinstance(document_number, str) and document_number.strip():
                identity_lines.insert(0, f"Drawing No. {document_number.strip()}")
            if isinstance(revision, str) and revision.strip():
                identity_lines.append(f"Revision {revision.strip()}")
            preview_snippet = "\n".join(identity_lines)
            parse_filename = f"split-sheet{_extension(filename)}"
    parsed = parse_document_metadata(
        file_name=parse_filename,
        filed_path=filed_path,
        source_path=source_path,
        preview_snippet=preview_snippet,
    )
    if parsed.confidence == "low":
        return filename
    return parsed.canonical_file_name


def _split_metadata_to_preserve(metadata: object) -> dict[str, object]:
    if not isinstance(metadata, dict) or not metadata.get("split_from"):
        return {}
    return {
        key: value
        for key, value in metadata.items()
        if key.startswith("split_") or key in _SPLIT_IDENTITY_KEYS
    }


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

    preserved_metadata: dict[str, object] = {}
    if record.source_document_id is not None:
        source_document = await session.get(SourceDocument, record.source_document_id)
        preserved_metadata = _split_metadata_to_preserve(
            getattr(source_document, "document_metadata", None)
        )

    content = await asyncio.to_thread(
        download_project_file,
        storage_key=record.storage_key,
    )
    destination_key = build_storage_key(str(project.id), destination_workspace_path)

    await asyncio.to_thread(
        upload_project_file,
        storage_key=destination_key,
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
    if source_doc_id is not None and preserved_metadata:
        destination_document = await session.get(SourceDocument, source_doc_id)
        current_metadata = getattr(destination_document, "document_metadata", None)
        if isinstance(current_metadata, dict):
            destination_document.document_metadata = {
                **current_metadata,
                **preserved_metadata,
            }

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
    await session.commit()

    # Storage cannot participate in the database transaction. Keep the inbox
    # object until the replacement row is durable, so a deadlock can only leave
    # a harmless duplicate blob for a later cleanup rather than an orphaned row.
    await asyncio.to_thread(delete_project_files, storage_keys=[record.storage_key])
    return moved


async def sort_inbox_files(
    session: AsyncSession,
    *,
    project: Project,
    manifest_version_hint: int = 0,
    workspace_paths: set[str] | None = None,
) -> SortFilesResult:
    inbox_prefix = _inbox_prefix(project)
    inbox_files = await list_workspace_files_under_prefix(
        session,
        project_id=project.id,
        path_prefix=inbox_prefix,
    )
    if workspace_paths is not None:
        inbox_files = [record for record in inbox_files if record.workspace_path in workspace_paths]

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

        if record.ingest_status in {"pending", "queued", "ingesting"}:
            result.records.append(
                SortFileRecord(
                    source_path=record.workspace_path,
                    filename=record.filename,
                    outcome="skipped",
                    reason="Ingestion is still in progress",
                )
            )
            result.counts.skipped += 1
            continue

        if record.ingest_status == "failed":
            result.records.append(
                SortFileRecord(
                    source_path=record.workspace_path,
                    filename=record.filename,
                    outcome="skipped",
                    reason="Ingestion failed; retry the upload before sorting",
                )
            )
            result.counts.skipped += 1
            continue

        result.counts.inspected += 1
        previews = await _file_previews(record)
        destination_folder = classify_inbox_destination(
            workspace_path=record.workspace_path,
            filename=record.filename,
            project_workspace_path=project.workspace_path,
            preview_snippet=previews.classification,
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

        source_document = (
            await session.get(SourceDocument, record.source_document_id)
            if record.source_document_id is not None
            else None
        )
        document_metadata = getattr(source_document, "document_metadata", None)
        destination_filename = await _resolve_destination_filename(
            source_path=record.workspace_path,
            destination_folder=destination_folder,
            filename=record.filename,
            project=project,
            preview_snippet=previews.for_identity,
            document_metadata=(
                document_metadata if isinstance(document_metadata, dict) else None
            ),
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
                    preview_snippet=previews.for_identity,
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
            preview_snippet=previews.for_identity,
        )
        filed_doc_id = await asyncio.to_thread(
            source_document_id_for_path,
            destination_path,
            project_id=project.id,
        )
        if filed_doc_id is not None:
            filed_document = await session.get(SourceDocument, filed_doc_id)
            if isinstance(filed_document, SourceDocument):
                upsert_consultant_fact_from_document(project, filed_document)
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
