from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cost_plan.models import CostPlanVersion
from app.database.draft_artifact import DraftArtifact
from app.database.project_document_selection import ProjectDocumentSelection
from app.database.workflow_run import WorkflowRun
from app.projects.workflow_capabilities import workflow_capabilities
from app.schemas.project_snapshot import (
    ProjectNextAction,
    ProjectSnapshot,
    ProjectSnapshotArtefact,
    ProjectSnapshotBudget,
    ProjectSnapshotSelection,
    ProjectSnapshotTender,
    ProjectSnapshotWorkflowRun,
)

MAX_ROLLUP_ROWS = 100


async def enrich_project_snapshot(
    session: AsyncSession, snapshot: ProjectSnapshot
) -> ProjectSnapshot:
    """Add project-wide read projections without importing workflow-owned models."""
    project_id = snapshot.identity.project_id
    selection_rows = list(
        (
            await session.execute(
                select(ProjectDocumentSelection)
                .where(ProjectDocumentSelection.project_id == project_id)
                .order_by(ProjectDocumentSelection.purpose.asc())
                .limit(MAX_ROLLUP_ROWS)
            )
        )
        .scalars()
        .all()
    )
    artefact_rows = list(
        (
            await session.execute(
                select(DraftArtifact)
                .where(DraftArtifact.project_id == project_id)
                .order_by(
                    DraftArtifact.workflow_type.asc(), DraftArtifact.version.desc()
                )
                .limit(MAX_ROLLUP_ROWS)
            )
        )
        .scalars()
        .all()
    )
    run_rows = list(
        (
            await session.execute(
                select(WorkflowRun)
                .where(
                    WorkflowRun.project_id == project_id,
                    WorkflowRun.state.in_(("queued", "running", "failed")),
                )
                .order_by(WorkflowRun.created_at.desc())
                .limit(MAX_ROLLUP_ROWS)
            )
        )
        .scalars()
        .all()
    )
    cost_plan = (
        await session.execute(
            select(CostPlanVersion)
            .where(CostPlanVersion.project_id == project_id)
            .order_by(CostPlanVersion.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    latest_artefacts = _latest_artefacts(artefact_rows)
    active_runs = [_run(row) for row in run_rows if row.state in {"queued", "running"}]
    failed_runs = [_run(row) for row in run_rows if row.state == "failed"]
    enriched = snapshot.model_copy(
        update={
            "purpose_selections": [
                ProjectSnapshotSelection(purpose=row.purpose, revision=row.revision)
                for row in selection_rows
            ],
            "latest_artefacts": latest_artefacts,
            "active_workflow_runs": active_runs,
            "failed_workflow_runs": failed_runs,
            "tender": _tender_projection(artefact_rows),
            "budget": _budget_projection(cost_plan),
        }
    )
    return enriched.model_copy(update={"next_actions": project_next_actions(enriched)})


def project_next_actions(snapshot: ProjectSnapshot) -> list[ProjectNextAction]:
    """Return deterministic, capability-gated actions for both UI and agents."""
    actions: list[ProjectNextAction] = []
    project_id = str(snapshot.identity.project_id)
    route = f"/projects/{project_id}"
    capabilities = workflow_capabilities(snapshot).capabilities

    missing_profile = sorted(
        {
            field
            for capability in capabilities.values()
            if capability.status == "needs_input"
            for field in capability.required_fields
        }
    )
    if missing_profile:
        actions.append(
            _action(
                "complete_project_profile",
                "Complete project profile",
                f"Required profile fields are missing: {', '.join(missing_profile)}.",
                f"missing_profile_fields:{','.join(missing_profile)}",
                route,
                "update_project_profile",
            )
        )
    if snapshot.evidence.ingest_failure_count:
        actions.append(
            _action(
                "resolve_ingest_failures",
                "Resolve ingest failures",
                f"{snapshot.evidence.ingest_failure_count} project file(s) failed ingestion.",
                f"ingest_failure_count:{snapshot.evidence.ingest_failure_count}",
                route,
                "list_project_files",
            )
        )
    elif snapshot.evidence.active_count == 0:
        actions.append(
            _action(
                "upload_project_evidence",
                "Upload project evidence",
                "No active project evidence is indexed.",
                "active_evidence_count:0",
                route,
                "list_project_files",
            )
        )

    for run in snapshot.active_workflow_runs:
        actions.append(
            _action(
                f"monitor_{run.workflow_type}",
                "Review workflow progress",
                f"{run.workflow_type} is {run.state}.",
                f"workflow_run:{run.run_id}:{run.state}",
                route,
                "get_workflow_run",
            )
        )

    artefacts = {item.workflow_type: item for item in snapshot.latest_artefacts}
    _append_capability_action(
        actions,
        capabilities,
        capability="create_pmp",
        when="create_pmp" not in artefacts,
        action=_action(
            "create_project_plan",
            "Create Project Plan",
            "No Project Plan artefact exists yet.",
            "latest_project_plan:none",
            route,
            "start_create_project_plan",
        ),
    )
    _append_capability_action(
        actions,
        capabilities,
        capability="create_cost_plan",
        when=snapshot.budget.status == "not_available",
        action=_action(
            "create_cost_plan",
            "Create Cost Plan",
            "No typed Cost Plan exists yet.",
            "typed_cost_plan:none",
            route,
            "start_create_cost_plan",
        ),
    )

    tender_selected = any(
        item.purpose == "tender_comparison" and item.revision > 0
        for item in snapshot.purpose_selections
    )
    _append_capability_action(
        actions,
        capabilities,
        capability="tender_comparison",
        when=not tender_selected,
        action=_action(
            "select_tender_quotes",
            "Select tender quotes",
            "No persisted Tender Comparison quote selection exists.",
            "tender_selection:none",
            f"{route}/tender",
            "replace_tender_quote_selection",
        ),
    )
    _append_capability_action(
        actions,
        capabilities,
        capability="tender_comparison",
        when=tender_selected and snapshot.tender.status == "not_started",
        action=_action(
            "start_tender_comparison",
            "Start Tender Comparison",
            "Tender quotes are selected but no comparison report exists.",
            "tender_report:none",
            f"{route}/tender",
            "start_tender_comparison",
        ),
    )
    if snapshot.tender.open_qa_count:
        actions.append(
            _action(
                "resolve_tender_qa",
                "Resolve Tender QA",
                f"{snapshot.tender.open_qa_count} mandatory QA item(s) remain open.",
                f"tender_open_qa_count:{snapshot.tender.open_qa_count}",
                f"{route}/tender",
                "get_tender_qa_queue",
            )
        )

    for artefact in snapshot.latest_artefacts:
        if not artefact.is_stale:
            continue
        capability = {
            "create_pmp": "update_pmp",
            "create_cost_plan": "refresh_cost_plan",
        }.get(artefact.workflow_type)
        if capability is None:
            continue
        _append_capability_action(
            actions,
            capabilities,
            capability=capability,
            when=True,
            action=_action(
                f"refresh_{artefact.workflow_type}",
                f"Refresh {artefact.title}",
                artefact.stale_reason or "An upstream project dependency changed.",
                f"stale_artefact:{artefact.artefact_id}",
                route,
                "start_refresh_project_plan"
                if capability == "update_pmp"
                else "start_refresh_cost_plan",
            ),
        )
    return actions


def _latest_artefacts(rows: Iterable[Any]) -> list[ProjectSnapshotArtefact]:
    latest: dict[str, ProjectSnapshotArtefact] = {}
    for row in rows:
        if row.workflow_type in latest:
            continue
        latest[row.workflow_type] = ProjectSnapshotArtefact(
            artefact_id=row.id,
            workflow_type=row.workflow_type,
            title=row.title,
            version=row.version,
            status=row.status,
            is_stale=bool(row.is_stale),
            stale_reason=row.stale_reason,
        )
    return list(latest.values())


def _run(row: Any) -> ProjectSnapshotWorkflowRun:
    return ProjectSnapshotWorkflowRun(
        run_id=row.id,
        workflow_type=row.workflow_type,
        state=row.state,
        error_class=row.error_class,
    )


def _tender_projection(rows: Iterable[Any]) -> ProjectSnapshotTender:
    report = next((row for row in rows if row.workflow_type == "tender_report"), None)
    if report is None:
        return ProjectSnapshotTender()
    provenance = report.provenance_metadata or {}
    quality = provenance.get("quality")
    quality = quality if isinstance(quality, dict) else {}
    open_qa_count = int(
        quality.get("open_qa_count", provenance.get("open_qa_count", 0)) or 0
    )
    approved = report.status == "accepted" and bool(provenance.get("frozen"))
    return ProjectSnapshotTender(
        status="approved" if approved else "qa_required" if open_qa_count else "draft",
        report_id=report.id,
        report_version=report.version,
        open_qa_count=open_qa_count,
        qs_gate_passed=bool(
            quality.get("qs_gate_passed", provenance.get("qs_gate_passed", False))
        ),
    )


def _budget_projection(row: Any | None) -> ProjectSnapshotBudget:
    if row is None:
        return ProjectSnapshotBudget()
    totals = row.deterministic_totals or {}
    total = totals.get("total_including_gst") or totals.get("total")
    return ProjectSnapshotBudget(
        status="accepted" if row.status == "accepted" else "proposed",
        version=row.version,
        total=str(total) if total is not None else None,
        gst_treatment=row.gst_treatment,
    )


def _append_capability_action(
    actions: list[ProjectNextAction],
    capabilities: dict[str, Any],
    *,
    capability: str,
    when: bool,
    action: ProjectNextAction,
) -> None:
    if when and capabilities[capability].status == "supported":
        actions.append(action)


def _action(
    code: str, label: str, reason: str, blocking_fact: str, route: str, tool: str
) -> ProjectNextAction:
    return ProjectNextAction(
        code=code,
        label=label,
        reason=reason,
        blocking_fact=blocking_fact,
        route=route,
        tool=tool,
    )
