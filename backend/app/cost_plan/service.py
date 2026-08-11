from __future__ import annotations

import re
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cost_plan.calculations import calculate_totals, optional_budget
from app.cost_plan.deletion_blockers import (
    collect_cost_item_deletion_blockers,
    raise_if_blocked,
)
from app.cost_plan.dependencies import stale_reasons
from app.cost_plan.models import CostPlanItem, CostPlanVersion
from app.cost_plan.renderer import render_cost_plan_markdown
from app.cost_plan.schemas import (
    CostItemInput,
    CostPlanMutationResult,
    CostPlanBatchMutationResult,
    CostPlanDelta,
    CostPlanOperation,
    CostPlanState,
    DependencySnapshot,
    ExternalCostProposal,
)
from app.database.draft_artifacts import get_latest_draft_artifact
from app.database.project import Project
from app.inbox.paths import build_storage_key
from app.projects.artefact_revisions import (
    ArtefactPolicyViolation,
    ArtefactRevisionConflict,
    ExportSpec,
    publish,
)
from app.projects.generation_audit import carry_generation_audit
from app.schemas.project_snapshot import ProjectSnapshot


class CostPlanNotFound(LookupError):
    pass


class CostPlanStaleError(ArtefactRevisionConflict):
    pass


DEFAULT_COST_PLAN_CATEGORIES = (
    "Fees and Charges",
    "Consultants",
    "Construction",
    "Contingency",
)

_ITEM_VARIATION_FIELDS = ("forecast_variations", "approved_variations")


def _apply_item_variations(
    narrative: dict,
    *,
    item_key: str,
    values: dict,
) -> None:
    """Persist editable variation columns on narrative until a variation register exists."""
    updates = {
        field: values.pop(field)
        for field in _ITEM_VARIATION_FIELDS
        if field in values
    }
    if not updates:
        return
    item_variations = dict(narrative.get("item_variations") or {})
    current = dict(item_variations.get(item_key) or {})
    for field, raw in updates.items():
        amount = Decimal(str(raw or "0"))
        current[field] = f"{amount.quantize(Decimal('0.01'))}"
    item_variations[item_key] = current
    narrative["item_variations"] = item_variations


def _seed_default_categories(categories: list[str]) -> list[str]:
    if categories:
        return categories
    return list(DEFAULT_COST_PLAN_CATEGORIES)


async def complete_cost_plan_state(
    session: AsyncSession,
    *,
    project: Project,
    state: CostPlanState,
) -> CostPlanState:
    """Restore missing taxonomy identities without overwriting existing facts."""
    from app.sitewise.cost_plan_evidence import CostPlanEvidencePack
    from app.sitewise.cost_plan_lines import cost_plan_lines
    from app.sitewise.mobilisation_evidence import MobilisationEvidencePack

    pack = CostPlanEvidencePack(
        mobilisation=MobilisationEvidencePack(),
    )
    try:
        scaffold = cost_plan_lines(project, pack).lines
    except ValueError:
        return state
    existing_codes = {item.cost_code for item in state.items}
    used_keys = {item.item_key for item in state.items}
    additions: list[CostItemInput] = []
    for line in scaffold:
        if line.cost_code in existing_codes:
            continue
        item_key = re.sub(r"[^a-z0-9]+", "-", line.cost_code.lower()).strip("-")
        if item_key in used_keys:
            item_key = f"scaffold:{item_key}"
        used_keys.add(item_key)
        budget = Decimal(str(line.budget)) if line.budget is not None else None
        allowance_type = (
            "contingency"
            if line.category == "Contingency / allowances"
            else "pc"
            if line.category in {"PC allowances", "Client-direct and landlord works"}
            else "none"
        )
        additions.append(
            CostItemInput(
                item_key=item_key,
                cost_code=line.cost_code,
                category=line.category,
                item=line.cost_item,
                budget=budget,
                allowance_type=allowance_type,
                basis=line.basis,
                source_refs=[{"kind": "cost_plan_taxonomy_scaffold"}],
                status="proposed",
            )
        )
    if not additions:
        return state
    return state.model_copy(
        update={"items": sorted([*state.items, *additions], key=_cost_item_sort_key)},
        deep=True,
    )


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
                display_order=item.display_order,
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
        key=lambda item: (item.display_order or 10**9, _cost_item_sort_key(item)),
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
    mutation: dict | None = None,
) -> CostPlanState:
    if project.owner_user_id != author_user_id:
        raise ArtefactPolicyViolation("project is not owned by the user")
    version = expected_base_version + 1
    complete_state = await complete_cost_plan_state(
        session,
        project=project,
        state=state,
    )
    proposed = complete_state.model_copy(
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
    prior_draft = None
    if expected_base_version >= 1:
        prior_draft = await get_latest_draft_artifact(
            session,
            project_id=project.id,
            workflow_type="create_cost_plan",
        )
    audit = carry_generation_audit(
        prior_draft.provenance_metadata if prior_draft is not None else None,
        mutation={
            "kind": "cost_plan_edit",
            "actor_source": actor_source,
            "from_version": expected_base_version,
            "to_version": version,
            **(mutation or {}),
        }
        if mutation is not None or expected_base_version >= 1
        else None,
    )
    provenance = {
        "typed_cost_plan": True,
        "dependency_snapshot": proposed.dependency_snapshot.model_dump(mode="json"),
        **audit,
    }
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
        provenance=provenance,
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
            display_order=item.display_order or index,
            budget=optional_budget(item),
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
        for index, item in enumerate(proposed.items, start=1)
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
    actor_source: str = "process_invoices",
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
        actor_source=actor_source,
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
    items = list(base.items)
    existing_index = next(
        (
            index
            for index, existing in enumerate(items)
            if existing.item_key == item.item_key
        ),
        None,
    )
    if existing_index is None:
        next_order = max((existing.display_order for existing in items), default=0) + 1
        items.append(item.model_copy(update={"display_order": next_order}))
    else:
        items[existing_index] = item.model_copy(
            update={"display_order": items[existing_index].display_order}
        )
    state = await _publish_state(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        state=base.model_copy(update={"items": items}),
        actor_source=actor_source,
    )
    return CostPlanMutationResult(state=state, changed_item_keys=[item.item_key])


async def apply_cost_plan_operations(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    operations: list[CostPlanOperation],
    current_snapshot: ProjectSnapshot | None = None,
    actor_source: str = "cost_plan_operation",
) -> CostPlanBatchMutationResult:
    """Apply a validated operation batch in one revision and one transaction."""
    if not operations or len(operations) > 50:
        raise ValueError("operations must contain between 1 and 50 items")
    base = await _base_for_mutation(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        current_snapshot=current_snapshot,
    )
    items = [item.model_copy(deep=True) for item in base.items]
    narrative = dict(base.narrative)
    categories = _seed_default_categories(
        [
            value
            for value in narrative.get("categories", [])
            if isinstance(value, str) and value.strip()
        ]
    )
    changed: list[str] = []
    deleted: list[str] = []

    for operation in operations:
        if operation.target_type == "cost_category":
            category = str(
                operation.values.get("category") or operation.target_id or ""
            ).strip()
            if not category:
                raise ValueError("cost category name is required")
            if operation.operation == "ADD":
                if category not in categories:
                    categories.append(category)
                continue
            if operation.operation == "DELETE":
                if any(item.category == category for item in items):
                    raise ArtefactPolicyViolation(
                        f"Cannot delete non-empty cost category {category!r}"
                    )
                categories = [value for value in categories if value != category]
                continue
            raise ValueError("cost categories support ADD and DELETE only")

        index = next(
            (
                position
                for position, item in enumerate(items)
                if item.item_key == operation.target_id
            ),
            None,
        )
        if operation.operation == "ADD":
            values = dict(operation.values)
            variation_updates = {
                field: values.pop(field)
                for field in _ITEM_VARIATION_FIELDS
                if field in values
            }
            item = CostItemInput.model_validate(
                {**values, "status": values.get("status", "manual")}
            )
            if any(existing.item_key == item.item_key for existing in items):
                raise ValueError(f"cost item {item.item_key!r} already exists")
            if variation_updates:
                _apply_item_variations(
                    narrative,
                    item_key=item.item_key,
                    values=variation_updates,
                )
            items.append(item)
            changed.append(item.item_key)
            continue
        if index is None:
            raise ValueError(f"cost item {operation.target_id!r} was not found")
        current = items[index]
        if operation.operation == "UPDATE":
            values = dict(operation.values)
            _apply_item_variations(
                narrative,
                item_key=current.item_key,
                values=values,
            )
            updated = CostItemInput.model_validate(
                {
                    **current.model_dump(mode="python"),
                    **values,
                    "item_key": current.item_key,
                    "status": "manual",
                }
            )
            items[index] = updated
            changed.append(updated.item_key)
            continue
        if operation.operation == "DELETE":
            raise_if_blocked(
                item_key=current.item_key,
                blockers=await collect_cost_item_deletion_blockers(
                    session,
                    project_id=project.id,
                    item=current,
                ),
            )
            items.pop(index)
            deleted.append(current.item_key)
            item_variations = dict(narrative.get("item_variations") or {})
            item_variations.pop(current.item_key, None)
            narrative["item_variations"] = item_variations
            continue
        if operation.operation == "DUPLICATE":
            values = dict(operation.values)
            copy_key = str(values.get("item_key") or f"{current.item_key}-copy")
            copy_code = str(values.get("cost_code") or f"{current.cost_code}-COPY")
            values.pop("forecast_variations", None)
            values.pop("approved_variations", None)
            duplicate = CostItemInput.model_validate(
                {
                    **current.model_dump(mode="python"),
                    **values,
                    "item_key": copy_key,
                    "cost_code": copy_code,
                    "status": "manual",
                    "locked": False,
                }
            )
            if any(
                item.item_key == copy_key or item.cost_code == copy_code
                for item in items
            ):
                raise ValueError("duplicate item_key and cost_code must be unique")
            items.insert(index + 1, duplicate)
            source_variations = dict(
                (narrative.get("item_variations") or {}).get(current.item_key) or {}
            )
            if source_variations:
                item_variations = dict(narrative.get("item_variations") or {})
                item_variations[copy_key] = source_variations
                narrative["item_variations"] = item_variations
            changed.append(duplicate.item_key)
            continue
        reference_index = next(
            (
                position
                for position, item in enumerate(items)
                if item.item_key == operation.reference_id
            ),
            None,
        )
        if reference_index is None:
            raise ValueError(
                f"reference cost item {operation.reference_id!r} was not found"
            )
        moving = items.pop(index)
        reference_index = next(
            position
            for position, item in enumerate(items)
            if item.item_key == operation.reference_id
        )
        destination = reference_index + (1 if operation.placement == "after" else 0)
        items.insert(destination, moving)
        changed.append(moving.item_key)

    ordered = [
        item.model_copy(update={"display_order": index, "cost_code": str(index)})
        for index, item in enumerate(items, start=1)
    ]
    # Drop empty categories only after item deletes so "Add category" can persist
    # until the user creates rows (or clears the last row in that category).
    if deleted:
        used_categories = {item.category for item in ordered}
        categories = [category for category in categories if category in used_categories]
    state = await _publish_state(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=expected_base_version,
        state=base.model_copy(
            update={
                "items": ordered,
                "narrative": {**narrative, "categories": categories},
            }
        ),
        actor_source=actor_source,
        mutation={
            "operations": [
                operation.model_dump(mode="json") for operation in operations
            ],
            "changed_item_keys": list(dict.fromkeys(changed)),
            "deleted_item_keys": list(dict.fromkeys(deleted)),
        },
    )
    changed_set = set(changed)
    return CostPlanBatchMutationResult(
        state=state,
        delta=CostPlanDelta(
            version=state.version,
            changed_items=[
                item for item in state.items if item.item_key in changed_set
            ],
            deleted_item_keys=list(dict.fromkeys(deleted)),
            totals=state.totals,
            workbook_status="pending",
        ),
    )


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
