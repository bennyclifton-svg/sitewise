"""Create a reviewable, unissued transmittal from a frozen file selection."""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.document_context import SelectedTurnDocument
from app.config import settings
from app.database.draft_artifact import DraftArtifact
from app.database.draft_artifacts import create_draft_artifact, next_draft_version
from app.database.project import Project
from app.database.workspace_files import upsert_workspace_file
from app.inbox.paths import build_storage_key
from app.projects.artefact_revisions import set_export_result_for_path
from app.storage.project_files import upload_project_file
from ingest.hashing import bytes_content_hash

WORKFLOW_TYPE = "create_transmittal"
RUNTIME_NAME = "clerk-transmittal-v1"


@dataclass(frozen=True, slots=True)
class TransmittalResult:
    draft: DraftArtifact
    document_count: int
    recipient: str | None
    purpose: str | None


def transmittal_workspace_path(project: Project, *, version: int) -> str:
    root = project.workspace_path.rstrip("/")
    return f"{root}/05-procurement/00-transmittals/transmittal_v{version:02d}.draft.md"


def render_transmittal_markdown(
    *,
    project: Project,
    documents: list[SelectedTurnDocument],
    recipient: str | None,
    purpose: str | None,
) -> str:
    """Render a deterministic draft; it deliberately has no issue/send action."""
    if not documents:
        raise ValueError("At least one selected document is required for a transmittal.")

    rows = [
        "| # | Class | Document no. | Title | Rev | Category |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for index, document in enumerate(documents, start=1):
        rows.append(
            "| {index} | {document_class} | {number} | {title} | {revision} | {category} |".format(
                index=index,
                document_class=_table_value(_transmittal_class_label(document)),
                number=_table_value(document.document_number),
                title=_table_value(document.title),
                revision=_table_value(document.revision),
                category=_table_value(document.category),
            )
        )

    recipient_value = recipient or "TBC — confirm before issue"
    purpose_value = purpose or "Document transmittal"
    return "\n".join(
        [
            "# Transmittal",
            "",
            "> **Draft only — not issued or sent.** Confirm the recipient and issue details before distribution.",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Project | {_table_value(project.title)} |",
            f"| To | {_table_value(recipient_value)} |",
            f"| Purpose | {_table_value(purpose_value)} |",
            "",
            "## Documents transmitted",
            "",
            *rows,
            "",
            "## Issue controls",
            "",
            "- Verify recipient, distribution method, and any response due date before issue.",
            "- Issue only the document revisions listed above.",
            "- Record the issue date and transmittal reference when the draft is issued.",
            "",
        ]
    )


async def run_create_transmittal_workflow(
    session: AsyncSession,
    *,
    project: Project,
    user_id: uuid.UUID,
    selected_documents: list[dict[str, Any]],
    recipient: str | None,
    purpose: str | None,
) -> TransmittalResult:
    """Publish the durable transmittal draft and its matching workspace file."""
    documents = [
        SelectedTurnDocument.model_validate(document) for document in selected_documents
    ]
    if not documents:
        raise ValueError("At least one selected document is required for a transmittal.")
    if len({document.workspace_file_id for document in documents}) != len(documents):
        raise ValueError("A selected document was included more than once.")

    version = await next_draft_version(
        session, project_id=project.id, workflow_type=WORKFLOW_TYPE
    )
    markdown = render_transmittal_markdown(
        project=project,
        documents=documents,
        recipient=recipient,
        purpose=purpose,
    )
    workspace_path = transmittal_workspace_path(project, version=version)
    draft = await create_draft_artifact(
        session,
        project_id=project.id,
        workflow_type=WORKFLOW_TYPE,
        title=f"Transmittal v{version:02d}",
        workspace_path=workspace_path,
        author_user_id=user_id,
        content_markdown=markdown,
        model=None,
        runtime=RUNTIME_NAME,
        provenance_metadata={
            "status": "draft_not_issued",
            "recipient": recipient,
            "purpose": purpose,
            "selected_documents": [
                document.model_dump(mode="json") for document in documents
            ],
        },
        expected_base_version=version - 1,
        actor_source="transmittal_workflow",
    )
    await sync_transmittal_draft_workspace(
        session,
        project=project,
        draft=draft,
        markdown=markdown,
    )
    return TransmittalResult(
        draft=draft,
        document_count=len(documents),
        recipient=recipient,
        purpose=purpose,
    )


async def sync_transmittal_draft_workspace(
    session: AsyncSession,
    *,
    project: Project,
    draft: DraftArtifact,
    markdown: str | None = None,
) -> str:
    """Store the published draft at its immutable versioned workspace path."""
    canonical_path = transmittal_workspace_path(project, version=draft.version)
    if draft.workspace_path != canonical_path:
        draft.workspace_path = canonical_path
        await session.flush()
        await session.refresh(draft)

    content = (markdown or draft.content_markdown).encode("utf-8")
    filename = Path(canonical_path).name
    storage_key = build_storage_key(str(project.id), canonical_path)
    content_hash = bytes_content_hash(content)
    await asyncio.to_thread(
        upload_project_file,
        storage_key=storage_key,
        content=content,
        filename=filename,
    )
    await upsert_workspace_file(
        session,
        project_id=project.id,
        workspace_path=canonical_path,
        filename=filename,
        storage_bucket=settings.supabase_storage_bucket,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=len(content),
        ingest_status="generated",
        ingest_error=None,
        source_document_id=None,
    )
    await set_export_result_for_path(
        session,
        revision=draft,
        workspace_path=canonical_path,
        content_hash=content_hash,
    )
    return canonical_path


def _transmittal_class_label(document: SelectedTurnDocument) -> str | None:
    cls = (document.document_class or "").strip()
    if cls == "drawing":
        return "drawing"
    return cls or None


def _table_value(value: str | None) -> str:
    if not value:
        return "—"
    return re.sub(r"\s+", " ", value).replace("|", "\\|").strip() or "—"
