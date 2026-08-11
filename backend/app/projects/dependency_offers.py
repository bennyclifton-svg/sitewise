"""Accept/reject flows for cross-artefact dependency update offers."""

from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.cost_plan.service import get_cost_plan
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.procurement.requests import list_procurement_requests
from app.projects.artefact_adapters import revise_workflow_artefact
from app.projects.artefact_blocks import markdown_blocks
from app.projects.dependencies import (
    AffectedArtefact,
    DependencyUpdateOffer,
    apply_deterministic_reference_update,
    apply_deterministic_text_replace,
    clear_consumed_dependency_entries,
    get_dependency_offer,
    list_dependency_offers,
    reject_dependency_offer as dismiss_dependency_offer,
    resolve_concrete_affected,
)
from app.sitewise.section_contracts import section_id_for_heading


class DependencyOfferAcceptResult(BaseModel):
    offer: DependencyUpdateOffer | None
    updated_artefact_types: tuple[str, ...] = ()
    skipped_protected: tuple[str, ...] = ()


GetDraft = Callable[[AsyncSession, uuid.UUID], Awaitable[DraftArtifact | None]]
ReviseDraft = Callable[..., Awaitable[DraftArtifact]]
UpdateCostLabels = Callable[..., list[str]]
SelectiveRefreshRunner = Callable[..., Awaitable[bool]]


async def enrich_dependency_offers(
    session: AsyncSession,
    *,
    project: Project,
    owner_user_id: uuid.UUID,
) -> list[DependencyUpdateOffer]:
    """Re-resolve pending offers against live drafts, RFPs and cost rows."""
    requests = await list_procurement_requests(session, project_id=project.id)
    request_rows = [
        {
            "id": str(row.id),
            "kind": row.kind,
            "target_slug": row.target_slug,
            "current_draft_artifact_id": (
                str(row.current_draft_artifact_id)
                if row.current_draft_artifact_id
                else None
            ),
        }
        for row in requests
    ]
    cost_items: list[dict[str, Any]] = []
    try:
        state = await get_cost_plan(
            session,
            project_id=project.id,
            owner_user_id=owner_user_id,
        )
        cost_items = [
            {
                "item_key": item.item_key,
                "category": item.category,
                "item": item.item,
            }
            for item in state.items
        ]
    except LookupError:
        pass

    pmp_blocks = await _pmp_blocks(session, project_id=project.id)
    offers = list_dependency_offers(project)
    enriched: list[DependencyUpdateOffer] = []
    metadata = dict(project.project_metadata or {})
    stored: list[dict[str, Any]] = []
    for offer in offers:
        artefacts = resolve_concrete_affected(
            [offer.category],
            source_kind=offer.source.kind,
            object_id=offer.source.object_id,
            previous_value=(
                {"name": offer.reference_patch["from"]}
                if offer.reference_patch
                else None
            ),
            new_value=(
                {"name": offer.reference_patch["to"]}
                if offer.reference_patch
                else None
            ),
            procurement_requests=request_rows,
            cost_items=cost_items,
            pmp_blocks=pmp_blocks,
        )
        # Preserve only artefact types still pending on the offer.
        pending_types = {item.artefact_type for item in offer.artefacts}
        artefacts = tuple(
            item for item in artefacts if item.artefact_type in pending_types
        )
        # Attach create_pmp draft id when available.
        artefacts = tuple(
            _attach_pmp_draft(item, pmp_blocks) for item in artefacts
        )
        updated = offer.model_copy(update={"artefacts": artefacts})
        enriched.append(updated)
        stored.append(updated.model_dump(mode="json"))
    if stored:
        metadata["dependency_offers"] = stored
        metadata["affected_artefacts"] = [
            item.model_dump(mode="json")
            for offer in enriched
            for item in offer.artefacts
        ]
        project.project_metadata = metadata
    return enriched


async def accept_dependency_offer(
    session: AsyncSession,
    *,
    project: Project,
    offer_id: str,
    artefact_types: Sequence[str],
    author_user_id: uuid.UUID,
    get_draft: GetDraft | None = None,
    revise_draft: ReviseDraft | None = None,
    update_cost_item_labels: UpdateCostLabels | None = None,
    run_selective_refresh: SelectiveRefreshRunner | None = None,
) -> DependencyOfferAcceptResult:
    offer = get_dependency_offer(project, offer_id)
    if offer is None:
        raise LookupError(f"dependency offer not found: {offer_id}")
    selected = {value for value in artefact_types}
    targets = [item for item in offer.artefacts if item.artefact_type in selected]
    if not targets:
        raise ValueError("no matching artefacts selected for accept")

    get_draft_fn = get_draft or _default_get_draft
    revise_fn = revise_draft or _default_revise
    refresh_fn = run_selective_refresh or _default_selective_refresh
    updated_types: list[str] = []
    skipped_protected: list[str] = []
    patched_drafts: set[uuid.UUID] = set()
    patch = offer.reference_patch or {}
    old_text = patch.get("from", "")
    new_text = patch.get("to", "")

    for target in targets:
        if target.update_mode == "selective_refresh":
            refreshed = await refresh_fn(
                session,
                project=project,
                author_user_id=author_user_id,
                target=target,
            )
            if refreshed:
                updated_types.append(target.artefact_type)
            continue
        if target.update_mode != "deterministic_reference" or not old_text:
            updated_types.append(target.artefact_type)
            continue
        if target.artefact_type == "cost_plan":
            if update_cost_item_labels is not None:
                changed = update_cost_item_labels(
                    session,
                    project=project,
                    item_keys=target.selector.cost_item_keys,
                    old_text=old_text,
                    new_text=new_text,
                )
            else:
                changed = await _update_cost_labels(
                    session,
                    project=project,
                    author_user_id=author_user_id,
                    item_keys=target.selector.cost_item_keys,
                    old_text=old_text,
                    new_text=new_text,
                )
            if changed:
                updated_types.append(target.artefact_type)
            continue

        draft_id = target.selector.draft_id
        if not draft_id:
            updated_types.append(target.artefact_type)
            continue
        draft_uuid = uuid.UUID(draft_id)
        if draft_uuid in patched_drafts:
            updated_types.append(target.artefact_type)
            continue
        draft = await get_draft_fn(session, draft_uuid)
        if draft is None or draft.project_id != project.id:
            raise LookupError(f"draft not found for offer artefact: {draft_id}")
        metadata = dict((draft.provenance_metadata or {}).get("blocks") or {})
        block_ids = target.selector.block_ids
        if not block_ids:
            # Section-level deterministic replace across unprotected blocks.
            block_ids = tuple(
                block.id
                for block in markdown_blocks(draft.content_markdown)
                if block.id
                and _block_in_sections(
                    draft.content_markdown,
                    block.start,
                    target.selector.section_ids,
                )
            )
        protected_skipped = tuple(
            block_id
            for block_id in block_ids
            if isinstance(metadata.get(block_id), dict)
            and metadata[block_id].get("user_protected")
        )
        if protected_skipped:
            skipped_protected.extend(protected_skipped)
        updated_markdown, _changed = apply_deterministic_reference_update(
            draft.content_markdown,
            metadata=metadata,
            block_ids=block_ids,
            old_text=old_text,
            new_text=new_text,
        )
        if updated_markdown != draft.content_markdown:
            await revise_fn(
                session=session,
                project=project,
                draft=draft,
                expected_base_version=draft.version,
                author_user_id=author_user_id,
                content_markdown=updated_markdown,
                actor_source="dependency_offer_accept",
            )
            patched_drafts.add(draft_uuid)
        updated_types.append(target.artefact_type)

    remaining = clear_consumed_dependency_entries(
        project,
        offer_id=offer_id,
        artefact_types=tuple(updated_types),
    )
    return DependencyOfferAcceptResult(
        offer=remaining if remaining.artefacts else None,
        updated_artefact_types=tuple(dict.fromkeys(updated_types)),
        skipped_protected=tuple(dict.fromkeys(skipped_protected)),
    )


def reject_dependency_offer_entries(
    project: Project,
    *,
    offer_id: str,
    artefact_types: Sequence[str] | None = None,
) -> None:
    dismiss_dependency_offer(
        project,
        offer_id=offer_id,
        artefact_types=artefact_types,
    )


async def _default_get_draft(
    session: AsyncSession, draft_id: uuid.UUID
) -> DraftArtifact | None:
    from app.database.draft_artifacts import get_draft_artifact

    return await get_draft_artifact(session, draft_id)


async def _default_revise(**kwargs) -> DraftArtifact:
    return await revise_workflow_artefact(**kwargs)


async def _default_selective_refresh(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    target: AffectedArtefact,
) -> bool:
    """Run baseline-aware narrative refresh for one dependency offer artefact."""
    section_ids = tuple(target.selector.section_ids or target.blocks)
    if target.artefact_type in {"pmp", "consultant_register"}:
        from app.workflows.update_pmp import run_update_pmp_workflow

        result = await run_update_pmp_workflow(
            session,
            user_id=author_user_id,
            project=project,
            thread_id=None,
            affected_section_ids=section_ids,
        )
        return result.status == "complete"

    if target.artefact_type == "rfp":
        from app.workflows.consultant_procurement import ConsultantDocument

        slug = target.selector.discipline_slug
        if not slug:
            return False
        from app.workflows.procurement_request import draft_procurement_request

        result = await draft_procurement_request(
            session,
            project=project,
            user_id=author_user_id,
            document=ConsultantDocument(),
            raw_target=slug.replace("_", " "),
            auto_commit=False,
            affected_section_ids=section_ids,
        )
        return result.draft is not None

    if target.artefact_type == "rft":
        from app.workflows.trade_procurement import TradeProcurementDocument
        from app.workflows.procurement_request import draft_procurement_request

        slug = target.selector.package_slug
        if not slug:
            return False
        result = await draft_procurement_request(
            session,
            project=project,
            user_id=author_user_id,
            document=TradeProcurementDocument("rft"),
            raw_target=slug.replace("_", " "),
            auto_commit=False,
            affected_section_ids=section_ids,
        )
        return result.draft is not None

    return False


async def _update_cost_labels(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    item_keys: Sequence[str],
    old_text: str,
    new_text: str,
) -> list[str]:
    from app.cost_plan.schemas import CostPlanOperation
    from app.cost_plan.service import apply_cost_plan_operations, get_cost_plan

    try:
        state = await get_cost_plan(
            session,
            project_id=project.id,
            owner_user_id=author_user_id,
        )
    except LookupError:
        return []
    wanted = set(item_keys)
    operations: list[CostPlanOperation] = []
    changed: list[str] = []
    for item in state.items:
        if item.item_key not in wanted:
            continue
        if old_text not in item.item:
            continue
        operations.append(
            CostPlanOperation(
                operation="UPDATE",
                target_type="cost_item",
                target_id=item.item_key,
                values={
                    "item": apply_deterministic_text_replace(
                        item.item, old_text=old_text, new_text=new_text
                    )
                },
            )
        )
        changed.append(item.item_key)
    if not operations:
        return []
    await apply_cost_plan_operations(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=state.version,
        operations=operations,
        actor_source="dependency_offer_accept",
    )
    return changed


async def _pmp_blocks(
    session: AsyncSession, *, project_id: uuid.UUID
) -> list[dict[str, Any]]:
    from app.database.draft_artifacts import get_latest_draft_artifact

    draft = await get_latest_draft_artifact(
        session,
        project_id=project_id,
        workflow_type="create_pmp",
    )
    if draft is None:
        return []
    blocks: list[dict[str, Any]] = []
    for block in markdown_blocks(draft.content_markdown):
        if not block.id:
            continue
        heading = _heading_at(draft.content_markdown, block.start)
        section_id = (
            section_id_for_heading(heading, work_type=None) if heading else None
        )
        blocks.append(
            {
                "id": block.id,
                "section_id": section_id or "",
                "content": block.content,
                "draft_id": str(draft.id),
            }
        )
    return blocks


def _attach_pmp_draft(
    item: AffectedArtefact, pmp_blocks: Sequence[dict[str, Any]]
) -> AffectedArtefact:
    if item.artefact_type not in {"pmp", "consultant_register"}:
        return item
    draft_id = next(
        (
            str(block.get("draft_id"))
            for block in pmp_blocks
            if block.get("draft_id")
        ),
        item.selector.draft_id,
    )
    if draft_id == item.selector.draft_id:
        return item
    return item.model_copy(
        update={
            "selector": item.selector.model_copy(update={"draft_id": draft_id})
        }
    )


def _block_in_sections(
    markdown: str, offset: int, section_ids: Sequence[str]
) -> bool:
    if not section_ids:
        return True
    heading = _heading_at(markdown, offset)
    if not heading:
        return False
    section_id = section_id_for_heading(heading, work_type=None)
    return section_id in set(section_ids)


def _heading_at(markdown: str, offset: int) -> str | None:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", markdown[:offset]))
    return matches[-1].group(1).strip() if matches else None
