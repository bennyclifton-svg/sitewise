from __future__ import annotations

import asyncio
import hashlib
import uuid
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import select

from app.database.draft_artifact import DraftArtifact
from app.config import settings
from app.database.workspace_files import upsert_workspace_file
from app.inbox.paths import build_storage_key
from app.storage.project_files import upload_project_file
from app.database.procurement_strategy import (
    ProcurementStrategy,
    ProcurementStrategyRow,
)
from app.projects.artefact_revisions import publish
from app.projects.events import publish_project_event


class CoreTenderArtefactPublisher:
    async def publish_draft(
        self,
        session: Any,
        *,
        project: Any,
        comparison_id: uuid.UUID,
        report_version: int,
        author_user_id: uuid.UUID,
        title: str,
        workspace_path: str,
        markdown: str,
        provenance: dict[str, Any] | None = None,
    ) -> uuid.UUID:
        provenance = provenance or {}
        row_id = provenance.get("row_id")
        workflow_type = (
            f"tender_report_{uuid.UUID(row_id)}" if row_id else "tender_report"
        )
        latest = (
            await session.execute(
                select(DraftArtifact)
                .where(
                    DraftArtifact.project_id == project.id,
                    DraftArtifact.workflow_type == workflow_type,
                )
                .order_by(DraftArtifact.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        result = await publish(
            session,
            project_id=project.id,
            workflow_type=workflow_type,
            expected_base_version=latest.version if latest is not None else 0,
            title=title,
            workspace_path=workspace_path,
            author_user_id=author_user_id,
            content_markdown=markdown,
            model=None,
            runtime="clerk-tender",
            provenance={
                **provenance,
                "comparison_id": str(comparison_id),
                "report_version": report_version,
                "watermark": "DRAFT",
            },
            actor_source="tender_report",
        )
        if row_id:
            content = markdown.encode("utf-8")
            storage_key = build_storage_key(str(project.id), workspace_path)
            filename = PurePosixPath(workspace_path).name
            await asyncio.to_thread(
                upload_project_file,
                storage_key=storage_key,
                content=content,
                filename=filename,
            )
            await upsert_workspace_file(
                session,
                project_id=project.id,
                workspace_path=workspace_path,
                filename=filename,
                storage_bucket=settings.supabase_storage_bucket,
                storage_key=storage_key,
                content_hash=hashlib.sha256(content).hexdigest(),
                size_bytes=len(content),
                ingest_status="generated",
            )
            row = await session.scalar(
                select(ProcurementStrategyRow)
                .join(ProcurementStrategy)
                .where(
                    ProcurementStrategy.project_id == project.id,
                    ProcurementStrategyRow.id == uuid.UUID(row_id),
                )
                .with_for_update()
            )
            if row is not None and row.comparison_id == comparison_id:
                row.recommendation_draft_id = result.revision.id
                row.recommendation_stale = row.submission_revision != provenance.get(
                    "submission_revision"
                )
                await session.flush()
        return result.revision.id

    async def read_markdown(self, session: Any, *, draft_id: uuid.UUID) -> str | None:
        draft = await session.get(DraftArtifact, draft_id)
        return draft.content_markdown if draft is not None else None

    async def read_projection(
        self, session: Any, *, draft_id: uuid.UUID
    ) -> dict[str, Any] | None:
        draft = await session.get(DraftArtifact, draft_id)
        if draft is None:
            return None
        return {
            "id": str(draft.id),
            "project_id": str(draft.project_id),
            "workflow_type": draft.workflow_type,
            "version": draft.version,
            "status": draft.status,
            "title": draft.title,
            "content_markdown": draft.content_markdown,
            "workspace_path": draft.workspace_path,
            "author_user_id": str(draft.author_user_id),
            "model": draft.model,
            "runtime": draft.runtime,
            "provenance_metadata": draft.provenance_metadata,
            "created_at": draft.created_at.isoformat(),
            "updated_at": draft.updated_at.isoformat(),
        }

    async def publish_approved(
        self,
        session: Any,
        *,
        draft_id: uuid.UUID,
        comparison_id: uuid.UUID,
        report_version: int,
        approved_by: uuid.UUID,
        html_path: str,
        pdf_path: str,
    ) -> None:
        if not html_path or not pdf_path:
            raise ValueError("immutable Tender HTML and PDF must both be ready")
        draft = await session.get(DraftArtifact, draft_id)
        if draft is None or draft.workflow_type != "tender_report":
            raise ValueError("Tender draft projection not found")
        draft.status = "accepted"
        draft.provenance_metadata = {
            **(draft.provenance_metadata or {}),
            "approved_by": str(approved_by),
            "comparison_id": str(comparison_id),
            "report_version": report_version,
            "immutable_html_path": html_path,
            "immutable_pdf_path": pdf_path,
            "frozen": True,
        }
        await session.flush()
        await publish_project_event(
            session,
            project_id=draft.project_id,
            actor_source="tender_report",
            resource_type="tender_report",
            resource_id=draft.id,
            resource_revision=draft.version,
            action="approved",
            payload={
                "comparison_id": str(comparison_id),
                "report_version": report_version,
                "html_ready": True,
                "pdf_ready": True,
            },
            deduplication_key=f"tender-report:{comparison_id}:{report_version}:approved",
        )
