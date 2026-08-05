from __future__ import annotations

import re
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cost_plan.calculations import calculate_totals, resolved_budget
from app.cost_plan.dependencies import stale_reasons
from app.cost_plan.models import CostPlanItem, CostPlanVersion
from app.cost_plan.renderer import render_cost_plan_markdown
from app.cost_plan.schemas import (
    CostItemInput,
    CostPlanMutationResult,
    CostPlanState,
    DependencySnapshot,
    ExternalCostProposal,
)
from app.database.project import Project
from app.inbox.paths import build_storage_key
from app.projects.artefact_revisions import (
    ArtefactPolicyViolation,
    ArtefactRevisionConflict,
    ExportSpec,
    publish,
)
from app.schemas.project_snapshot import ProjectSnapshot


class CostPlanNotFound(LookupError):
    pass


class CostPlanStaleError(ArtefactRevisionConflict):
    pass


def _cost_item_sort_key(item: CostItemInput) -> tuple[tuple[int, int | str], ...]:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in re.split(r"(\d+)", item.cost_code)
        if part
    )


def _state(row: CostPlanVersion) -> CostPlanState:
    items = sorted(
        [
            CostItemInput(
                item_key=item.item_key,
                cost_code=item.cost_code,
                category=item.category,
                item=item.item,
                budget=item.budget,
                committed=item.committed,
                forecast=item.forecast,
                paid=item.paid,
                allowance_type=item.allowance_type,
                quantity=item.quantity,
                unit=item.unit,
                rate=item.rate,
                basis=item.basis,
                source_refs=item.source_refs,
                confidence=item.confidence,
                status=item.status,
                locked=item.locked,
            )
            for item in row.items
        ],
        key=_cost_item_sort_key,
    )
    return CostPlanState(
        id=row.id,
        project_id=row.project_id,
        artefact_revision_id=row.artefact_revision_id,
        version=row.version,
        status=row.status,
        contingency_percent=row.contingency_percent,
        escalation_percent=row.escalation_percent,
        gst_treatment=row.gst_treatment,
        assumptions=row.assumptions,
        narrative=row.narrative,
        dependency_snapshot=DependencySnapshot.model_validate(row.dependency_snapshot),
        items=items,
        totals=calculate_totals(
            items,
            contingency_percent=row.contingency_percent,
            escalation_percent=row.escalation_percent,
            gst_treatment=row.gst_treatment,
        ),
    )


async def get_cost_plan(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    version: int | None = None,
) -> CostPlanState:
    statement = (
        select(CostPlanVersion)
        .join(Project, Project.id == CostPlanVersion.project_id)
        .where(
            CostPlanVersion.project_id == project_id,
            Project.owner_user_id == owner_user_id,
        )
        .options(selectinload(CostPlanVersion.items))
    )
    if version is None:
        statement = statement.order_by(CostPlanVersion.version.desc()).limit(1)
    else:
        statement = statement.where(CostPlanVersion.version == version)
    row = (await session.execute(statement)).scalar_one_or_none()
    if row is None:
        raise CostPlanNotFound(str(project_id))
    return _state(row)


async def _publish_state(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    state: CostPlanState,
    actor_source: str,
    source_draft_id: uuid.UUID | None = None,
    external_idempotency_key: str | None = None,
) -> CostPlanState:
    if project.owner_user_id != author_user_id:
        raise ArtefactPolicyViolation("project is not owned by the user")
    version = expected_base_version + 1
    proposed = state.model_copy(
        update={"version": version, "status": "proposed"}, deep=True
    )
    totals = calculate_totals(
        proposed.items,
        contingency_percent=proposed.contingency_percent,
        escalation_percent=proposed.escalation_percent,
        gst_treatment=proposed.gst_treatment,
    )
    proposed = proposed.model_copy(update={"totals": totals})
    markdown = render_cost_plan_markdown(proposed)
    base = f"{project.workspace_path.rstrip('/')}/01-cost"
    markdown_path = f"{base}/cost_plan_v{version:02d}.md"
    workbook_path = f"{base}/Cost_Plan_v{version:02d}.draft.xlsx"
    result = await publish(
        session,
        project_id=project.id,
        workflow_type="create_cost_plan",
        expected_base_version=expected_base_version,
        title=f"{project.title} Cost Plan",
        workspace_path=markdown_path,
        author_user_id=author_user_id,
        content_markdown=markdown,
        model=proposed.dependency_snapshot.model_version,
        runtime=proposed.dependency_snapshot.runtime_version,
        provenance={
            "typed_cost_plan": True,
            "dependency_snapshot": proposed.dependency_snapshot.model_dump(mode="json"),
        },
        actor_source=actor_source,
        exports=(
            ExportSpec(
                "workbook",
                workbook_path,
                build_storage_key(str(project.id), workbook_path),
            ),
        ),
    )
    row = CostPlanVersion(
        project_id=project.id,
        artefact_revision_id=result.revision.id,
        version=version,
        created_by_user_id=author_user_id,
        status="proposed",
        contingency_percent=proposed.contingency_percent,
        escalation_percent=proposed.escalation_percent,
        gst_treatment=proposed.gst_treatment,
        assumptions=proposed.assumptions,
        narrative=proposed.narrative,
        dependency_snapshot=proposed.dependency_snapshot.model_dump(mode="json"),
        deterministic_totals=totals.model_dump(mode="json"),
        source_draft_id=source_draft_id,
        external_idempotency_key=external_idempotency_key,
    )
    row.items = [
        CostPlanItem(
            item_key=item.item_key,
            cost_code=item.cost_code,
            category=item.category,
            item=item.item,
            budget=resolved_budget(item),
            committed=item.committed,
            forecast=item.forecast,
            paid=item.paid,
            allowance_type=item.allowance_type,
            quantity=item.quantity,
            unit=item.unit,
            rate=item.rate,
            basis=item.basis,
            source_refs=item.source_refs,
            confidence=item.confidence,
            status=item.status,
            locked=item.locked,
        )
        for item in proposed.items
    ]
    session.add(row)
    await session.flush()
    await session.refresh(row, attribute_names=["items"])
    return _state(row)


async def _base_for_mutation(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    current_snapshot: ProjectSnapshot | None,
) -> CostPlanState:
    base = await get_cost_plan(
        session,
        project_id=project.id,
        owner_user_id=author_user_id,
        version=expected_base_version,
    )
    latest = await get_cost_plan(
        session, project_id=project.id, owner_user_id=author_user_id
    )
    if latest.version != expected_base_version:
        raise ArtefactRevisionConflict(
            f"Expected Cost Plan v{expected_base_version}, current version is v{latest.version}"
        )
    if current_snapshot is not None:
        reasons = stale_reasons(base.dependency_snapshot, current_snapshot)
        if reasons:
            raise CostPlanStaleError("Cost Plan base is stale: " + ", ".join(reasons))
    return base


async def republish_cost_plan_for_ledger(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    dependency_snapshot: DependencySnapshot,
    external_idempotency_key: str,
) -> CostPlanState:
    """Publish unchanged budget state after a canonical ledger mutation."""
    base = await _base_for_mutation(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        current_snapshot=None,
    )
    state = base.model_copy(
        update={"dependency_snapshot": dependency_snapshot},
        deep=True,
    )
    return await _publish_state(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        state=state,
        actor_source="process_invoices",
        external_idempotency_key=external_idempotency_key,
    )


async def upsert_cost_item(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    item: CostItemInput,
    current_snapshot: ProjectSnapshot | None = None,
    actor_source: str = "cost_plan_tool",
) -> CostPlanMutationResult:
    base = await _base_for_mutation(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        current_snapshot=current_snapshot,
    )
    items = [existing for existing in base.items if existing.item_key != item.item_key]
    items.append(item)
    items.sort(key=_cost_item_sort_key)
    state = await _publish_state(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        state=base.model_copy(update={"items": items}),
        actor_source=actor_source,
    )
    return CostPlanMutationResult(state=state, changed_item_keys=[item.item_key])


async def set_contingency(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    percent: Decimal,
    current_snapshot: ProjectSnapshot | None = None,
) -> CostPlanMutationResult:
    if percent < 0:
        raise ValueError("contingency percent cannot be negative")
    base = await _base_for_mutation(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        current_snapshot=current_snapshot,
    )
    state = await _publish_state(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        state=base.model_copy(update={"contingency_percent": percent}),
        actor_source="cost_plan_tool",
    )
    return CostPlanMutationResult(state=state)


async def set_cost_plan_assumption(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    key: str,
    value: str,
    current_snapshot: ProjectSnapshot | None = None,
) -> CostPlanMutationResult:
    if not key.strip() or not value.strip():
        raise ValueError("assumption key and value are required")
    base = await _base_for_mutation(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        current_snapshot=current_snapshot,
    )
    assumptions = {**base.assumptions, key.strip(): value.strip()}
    state = await _publish_state(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        state=base.model_copy(update={"assumptions": assumptions}),
        actor_source="cost_plan_tool",
    )
    return CostPlanMutationResult(state=state)


async def refresh_cost_plan(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    current_snapshot: ProjectSnapshot,
    proposed_items: list[CostItemInput],
    dependency_snapshot: DependencySnapshot,
    assumptions: dict[str, str] | None = None,
    contingency_percent: Decimal | None = None,
    escalation_percent: Decimal | None = None,
) -> CostPlanMutationResult:
    base = await _base_for_mutation(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        current_snapshot=None,
    )
    by_key = {item.item_key: item for item in base.items}
    conflicts: list[str] = []
    changed: list[str] = []
    for proposal in proposed_items:
        current = by_key.get(proposal.item_key)
        if current is not None and (current.locked or current.status == "manual"):
            if proposal != current:
                conflicts.append(proposal.item_key)
            continue
        if current != proposal:
            by_key[proposal.item_key] = proposal
            changed.append(proposal.item_key)
    refreshed = base.model_copy(
        update={
            "items": sorted(by_key.values(), key=_cost_item_sort_key),
            "dependency_snapshot": dependency_snapshot,
            "assumptions": {**base.assumptions, **(assumptions or {})},
            "contingency_percent": (
                base.contingency_percent
                if contingency_percent is None
                else contingency_percent
            ),
            "escalation_percent": (
                base.escalation_percent
                if escalation_percent is None
                else escalation_percent
            ),
        }
    )
    state = await _publish_state(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        state=refreshed,
        actor_source="cost_plan_refresh",
    )
    return CostPlanMutationResult(
        state=state, changed_item_keys=changed, conflicts=conflicts
    )


async def apply_external_proposal(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    proposal: ExternalCostProposal,
    confirmed: bool,
    dependency_snapshot: DependencySnapshot,
) -> CostPlanState:
    if not confirmed:
        raise ArtefactPolicyViolation(
            "external Cost Plan proposal requires explicit confirmation"
        )
    if proposal.project_id != project.id:
        raise ArtefactPolicyViolation("external proposal belongs to another project")
    existing = (
        await session.execute(
            select(CostPlanVersion)
            .where(
                CostPlanVersion.project_id == project.id,
                CostPlanVersion.external_idempotency_key == proposal.idempotency_key,
            )
            .options(selectinload(CostPlanVersion.items))
        )
    ).scalar_one_or_none()
    if existing is not None:
        return _state(existing)
    base = await _base_for_mutation(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        current_snapshot=None,
    )
    by_key = {item.item_key: item for item in base.items}
    for item in proposal.items:
        by_key[item.item_key] = item
    state = base.model_copy(
        update={
            "items": sorted(
                by_key.values(), key=lambda value: (value.cost_code, value.item_key)
            ),
            "dependency_snapshot": dependency_snapshot,
            "narrative": {
                **base.narrative,
                "external_proposal": proposal.model_dump(mode="json"),
            },
        }
    )
    return await _publish_state(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        state=state,
        actor_source="approved_tender_handoff",
        external_idempotency_key=proposal.idempotency_key,
    )


async def accept_cost_plan_version(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    artefact_revision_id: uuid.UUID,
) -> bool:
    target = (
        await session.execute(
            select(CostPlanVersion).where(
                CostPlanVersion.project_id == project_id,
                CostPlanVersion.artefact_revision_id == artefact_revision_id,
            )
        )
    ).scalar_one_or_none()
    if target is None:
        return False
    accepted = list(
        (
            await session.execute(
                select(CostPlanVersion).where(
                    CostPlanVersion.project_id == project_id,
                    CostPlanVersion.status == "accepted",
                    CostPlanVersion.id != target.id,
                )
            )
        ).scalars()
    )
    for previous in accepted:
        previous.status = "superseded"
    target.status = "accepted"
    await session.flush()
    return True
