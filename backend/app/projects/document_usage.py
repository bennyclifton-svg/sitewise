"""Which project documents the latest drafts consulted or issued.

Workflows record what they read as source refs on the draft artefact
(``project_evidence:<relative_path>#chunk=<chunk_id>``). Procurement workflows
also freeze the complete outbound schedule in ``issued_document_refs``. Mapping
both sets back onto relative paths lets the repository mark every row consulted
or included in the selected artefact.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.draft_artifact import DraftArtifact
from app.schemas.projects import DocumentUsageMark


def relative_path_from_source_ref(ref: str) -> str | None:
    """Pull the workspace-relative path out of a workflow source ref."""
    candidate = (ref or "").strip()
    if not candidate:
        return None
    _, separator, remainder = candidate.partition(":")
    if separator:
        candidate = remainder
    candidate = candidate.partition("#")[0].replace("\\", "/").strip()
    return candidate or None


def usage_marks_by_relative_path(
    drafts: Iterable[DraftArtifact],
) -> dict[str, list[DocumentUsageMark]]:
    """Map each cited or issued path to the latest relevant drafts."""
    marks: dict[str, list[DocumentUsageMark]] = {}
    for draft in _latest_per_workflow(drafts):
        metadata = draft.provenance_metadata or {}
        refs = _draft_document_refs(metadata)
        if not refs:
            continue
        mark = DocumentUsageMark(
            artefact_id=draft.id,
            workflow_type=draft.workflow_type,
            title=draft.title,
            version=draft.version,
        )
        for path in _unique_paths(refs):
            marks.setdefault(path, []).append(mark)
    return {
        path: sorted(entries, key=lambda entry: entry.workflow_type)
        for path, entries in marks.items()
    }


async def latest_document_usage(
    session: AsyncSession, *, project_id: uuid.UUID
) -> dict[str, list[DocumentUsageMark]]:
    """Usage marks for the newest draft of each workflow type in a project."""
    stmt = (
        select(
            DraftArtifact.id,
            DraftArtifact.workflow_type,
            DraftArtifact.version,
            DraftArtifact.title,
            DraftArtifact.provenance_metadata,
        )
        .where(DraftArtifact.project_id == project_id)
        .distinct(DraftArtifact.workflow_type)
        .order_by(DraftArtifact.workflow_type, DraftArtifact.version.desc())
    )
    result = await session.execute(stmt)
    return usage_marks_by_relative_path(result.all())


def _latest_per_workflow(drafts: Iterable[DraftArtifact]) -> list[DraftArtifact]:
    latest: dict[str, DraftArtifact] = {}
    for draft in drafts:
        current = latest.get(draft.workflow_type)
        if current is None or draft.version > current.version:
            latest[draft.workflow_type] = draft
    return list(latest.values())


def _unique_paths(refs: Sequence[object]) -> list[str]:
    paths: list[str] = []
    for ref in refs:
        path = relative_path_from_source_ref(str(ref))
        if path is not None and path not in paths:
            paths.append(path)
    return paths


def _draft_document_refs(metadata: dict[object, object]) -> list[object]:
    refs: list[object] = []
    for key in ("evidence_refs", "issued_document_refs"):
        value = metadata.get(key)
        if isinstance(value, list):
            refs.extend(value)
    return refs
