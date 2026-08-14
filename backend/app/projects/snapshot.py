from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.database.project_decision import ProjectDecision
from app.database.project_profile_proposal import ProjectProfileProposal
from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile
from app.projects.profile import read_profile
from app.projects.project_intelligence import enrich_project_snapshot
from app.schemas.profile_proposals import ProjectProfileProposalView
from app.schemas.project_snapshot import (
    DOCUMENT_INGEST_FAILURE_DETAIL,
    EvidenceIngestFailure,
    ProjectSnapshot,
    ProjectSnapshotDecision,
    ProjectSnapshotDecisions,
    ProjectSnapshotEvidence,
    ProjectSnapshotIdentity,
    SnapshotValue,
)

MAX_EVIDENCE_FINGERPRINT_ROWS = 2_000
MAX_INGEST_FAILURE_ROWS = 100
MAX_DECISIONS = 200
MAX_OPEN_PROPOSALS = 100
MAX_CONTEXT_READ_ATTEMPTS = 3


class ProjectSnapshotNotFound(LookupError):
    pass


class ProjectSnapshotUnstable(RuntimeError):
    pass


def snapshot_content_fingerprint(snapshot: ProjectSnapshot) -> str:
    payload = snapshot.model_dump(
        mode="json", exclude={"generated_at", "content_fingerprint"}
    )
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _value(value: Any, *, source: str) -> SnapshotValue:
    if value in (None, "", [], {}):
        return SnapshotValue(status="needs_input")
    return SnapshotValue(status="confirmed", value=value, source=source)


def _taxonomy_metadata(project: Project) -> dict[str, Any]:
    metadata = project.project_metadata
    if not isinstance(metadata, dict):
        return {}
    taxonomy = metadata.get("taxonomy")
    return dict(taxonomy) if isinstance(taxonomy, dict) else {}


def _context_field_states(project: Project) -> dict[str, str]:
    raw = _taxonomy_metadata(project).get("field_states")
    if not isinstance(raw, dict):
        return {}
    allowed = {"explicitly_excluded", "not_applicable"}
    return {
        str(key): str(value)
        for key, value in raw.items()
        if isinstance(key, str) and value in allowed
    }


def _evidence_fingerprint(rows: list[Any]) -> str:
    parts = [
        {
            "id": str(row.id),
            "path": row.relative_path,
            "content_hash": row.content_hash,
        }
        for row in rows
    ]
    encoded = json.dumps(
        parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _selection_metadata(rows: list[Any]) -> dict[str, Any]:
    selections: dict[str, Any] = {}
    for row in rows:
        metadata = row.document_metadata
        if not isinstance(metadata, dict):
            continue
        selection = metadata.get("selection")
        if selection not in (None, "", [], {}):
            selections[row.relative_path] = selection
    return selections


async def get_project_snapshot(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    owner_user_id: uuid.UUID | None = None,
    generated_at: datetime | None = None,
    _context_read_attempt: int = 1,
) -> ProjectSnapshot:
    project_statement = select(Project).where(Project.id == project_id)
    if owner_user_id is not None:
        project_statement = project_statement.where(Project.owner_user_id == owner_user_id)
    project_result = await session.execute(project_statement)
    project = project_result.scalar_one_or_none()
    if project is None:
        raise ProjectSnapshotNotFound(str(project_id))

    decisions_result = await session.execute(
        select(ProjectDecision)
        .where(ProjectDecision.project_id == project.id)
        .order_by(ProjectDecision.decision_id.asc())
        .limit(MAX_DECISIONS + 1)
        .execution_options(populate_existing=True)
    )
    all_decision_rows = list(decisions_result.scalars().all())
    decisions_complete = len(all_decision_rows) <= MAX_DECISIONS
    decision_rows = all_decision_rows[:MAX_DECISIONS]

    proposals_result = await session.execute(
        select(ProjectProfileProposal)
        .where(
            ProjectProfileProposal.project_id == project.id,
            ProjectProfileProposal.state == "pending",
        )
        .order_by(ProjectProfileProposal.created_at.asc(), ProjectProfileProposal.id.asc())
        .limit(MAX_OPEN_PROPOSALS + 1)
        .execution_options(populate_existing=True)
    )
    all_proposal_rows = list(proposals_result.scalars().all())
    proposals_complete = len(all_proposal_rows) <= MAX_OPEN_PROPOSALS
    proposal_rows = all_proposal_rows[:MAX_OPEN_PROPOSALS]

    evidence_result = await session.execute(
        select(
            SourceDocument.id,
            SourceDocument.relative_path,
            SourceDocument.content_hash,
            SourceDocument.document_metadata,
            func.count().over().label("total_count"),
        )
        .where(
            SourceDocument.project_id == project.id,
            SourceDocument.source_type == "project_evidence",
        )
        .order_by(SourceDocument.relative_path.asc(), SourceDocument.id.asc())
        .limit(MAX_EVIDENCE_FINGERPRINT_ROWS)
    )
    evidence_rows = list(evidence_result.all())
    active_count = evidence_rows[0].total_count if evidence_rows else 0

    failures_result = await session.execute(
        select(
            WorkspaceFile.workspace_path,
            WorkspaceFile.ingest_error,
            func.count().over().label("total_count"),
        )
        .where(
            WorkspaceFile.project_id == project.id,
            WorkspaceFile.ingest_status.in_(("failed", "error")),
        )
        .order_by(WorkspaceFile.workspace_path.asc())
        .limit(MAX_INGEST_FAILURE_ROWS)
    )
    failure_rows = list(failures_result.all())
    failure_count = failure_rows[0].total_count if failure_rows else 0

    taxonomy = _taxonomy_metadata(project)
    snapshot_decisions = [
        ProjectSnapshotDecision(
            decision_id=row.decision_id,
            label=row.label,
            selected=row.selected,
            source=row.source,
            revision=row.revision,
            locked=row.locked,
            evidence_conflict=row.evidence_conflict,
            agent_suggestion=row.agent_suggestion,
        )
        for row in decision_rows
    ]
    locked_procurement = next(
        (
            row.selected
            for row in decision_rows
            if row.decision_id == "procurement-route" and row.locked
        ),
        None,
    )
    procurement_value = locked_procurement or taxonomy.get("procurement_route")
    procurement_source = (
        "project_decision" if locked_procurement is not None else "project_setup"
    )

    snapshot = ProjectSnapshot(
        generated_at=generated_at or datetime.now(UTC),
        content_fingerprint="pending",
        context_version=project.project_context_version or 1,
        field_states=_context_field_states(project),
        identity=ProjectSnapshotIdentity(
            project_id=project.id,
            title=project.title,
            slug=project.slug,
            workspace_path=project.workspace_path,
            phase=project.phase,
            status=project.status,
            site_address=_value(taxonomy.get("site_address"), source="project_setup"),
            client=_value(taxonomy.get("client"), source="project_setup"),
        ),
        profile=read_profile(project),
        decisions=ProjectSnapshotDecisions(
            set_revision=project.decision_set_revision,
            items=snapshot_decisions,
            open_count=sum(
                1
                for row in decision_rows
                if row.evidence_conflict or row.agent_suggestion is not None
            ),
            complete=decisions_complete,
        ),
        evidence=ProjectSnapshotEvidence(
            fingerprint=_evidence_fingerprint(evidence_rows),
            active_count=active_count,
            fingerprint_complete=active_count <= MAX_EVIDENCE_FINGERPRINT_ROWS,
            ingest_failure_count=failure_count,
            ingest_failures=[
                EvidenceIngestFailure(
                    workspace_path=row.workspace_path,
                    error=DOCUMENT_INGEST_FAILURE_DETAIL,
                )
                for row in failure_rows
            ],
            selection_metadata=_selection_metadata(evidence_rows),
        ),
        confirmed_inputs={
            "budget": _value(taxonomy.get("budget"), source="project_setup"),
            "timeframe": _value(taxonomy.get("timeframe"), source="project_setup"),
            "procurement_route": _value(
                procurement_value, source=procurement_source
            ),
        },
        open_profile_proposals=[
            ProjectProfileProposalView.model_validate(row) for row in proposal_rows
        ],
        open_profile_proposals_complete=proposals_complete,
    )
    enriched = await enrich_project_snapshot(session, snapshot)
    completed = enriched.model_copy(
        update={"content_fingerprint": snapshot_content_fingerprint(enriched)}
    )
    current_result = await session.execute(
        project_statement.execution_options(populate_existing=True)
    )
    current_project = current_result.scalar_one_or_none()
    if current_project is None:
        raise ProjectSnapshotNotFound(str(project_id))
    current_version = current_project.project_context_version or 1
    if current_version == completed.context_version:
        return completed
    if _context_read_attempt >= MAX_CONTEXT_READ_ATTEMPTS:
        raise ProjectSnapshotUnstable(
            f"project {project_id} context changed during "
            f"{MAX_CONTEXT_READ_ATTEMPTS} snapshot attempts"
        )
    return await get_project_snapshot(
        session,
        project_id=project_id,
        owner_user_id=owner_user_id,
        generated_at=generated_at,
        _context_read_attempt=_context_read_attempt + 1,
    )
