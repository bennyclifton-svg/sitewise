"""Explicit project-change dependencies for targeted artefact refreshes."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Sequence

from pydantic import BaseModel

from app.database.project import Project
from app.projects.artefact_blocks import markdown_blocks


DirtyCategory = Literal[
    "scope_dirty",
    "programme_dirty",
    "cost_dirty",
    "consultants_dirty",
    "ffe_dirty",
    "approvals_dirty",
    "design_dirty",
    "procurement_dirty",
]

ArtefactType = Literal["pmp", "rfp", "rft", "cost_plan", "consultant_register"]

_PROFILE_DIRTY: dict[str, tuple[DirtyCategory, ...]] = {
    "building_class": ("scope_dirty", "design_dirty", "cost_dirty"),
    "work_type": ("scope_dirty", "design_dirty", "cost_dirty", "procurement_dirty"),
    "subclasses": ("scope_dirty", "design_dirty", "cost_dirty"),
    "scale": ("scope_dirty", "cost_dirty", "programme_dirty"),
    "complexity": ("design_dirty", "approvals_dirty", "programme_dirty"),
    "work_scope": ("scope_dirty", "design_dirty", "cost_dirty", "procurement_dirty"),
    "state": ("approvals_dirty",),
    "client": ("consultants_dirty",),
    "site_address": ("scope_dirty", "approvals_dirty"),
}

_SECTION_BY_DIRTY_BLOCK: dict[str, str] = {
    "project_summary": "snapshot",
    "scope": "scope-client-requirements",
    "consultants": "consultants",
    "programme": "programme",
    "risks": "risks",
    "cost_planning": "cost-budget",
    "ffe": "ffe-schedule",
    "ffe-schedule": "ffe-schedule",
    "planning_and_compliance": "compliance-approvals",
    "design_management": "scope-client-requirements",
    "procurement_and_delivery": "procurement-delivery",
    "background": "background",
    "requested_services": "requested_services",
    "materials": "materials",
    "interfaces": "interfaces",
    "design_responsibility": "design_responsibility",
    "submission_requirements": "submission_requirements",
    "items": "items",
    "totals": "totals",
    "consultant_fees": "consultant_fees",
    "finishes": "finishes",
}


class ArtefactSelector(BaseModel):
    discipline_slug: str | None = None
    package_slug: str | None = None
    procurement_request_id: str | None = None
    draft_id: str | None = None
    draft_workflow_type: str | None = None
    section_ids: tuple[str, ...] = ()
    block_ids: tuple[str, ...] = ()
    cost_item_keys: tuple[str, ...] = ()
    shared_object_key: str | None = None


class AffectedArtefact(BaseModel):
    artefact_type: ArtefactType
    selector: ArtefactSelector
    blocks: tuple[str, ...] = ()
    update_mode: Literal["deterministic_reference", "selective_refresh"] = (
        "selective_refresh"
    )


class DirtyChangeSource(BaseModel):
    kind: str
    object_id: str
    revision: int | None = None


class DependencyUpdateOffer(BaseModel):
    id: str
    category: DirtyCategory
    source: DirtyChangeSource
    status: Literal["pending", "partial"] = "pending"
    artefacts: tuple[AffectedArtefact, ...]
    reference_patch: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class _Template:
    artefact_type: ArtefactType
    selector_kind: Literal[
        "project", "discipline", "package", "all_rfp", "all_rft"
    ]
    blocks: tuple[str, ...]


_DIRTY_TEMPLATES: dict[DirtyCategory, tuple[_Template, ...]] = {
    "scope_dirty": (
        _Template("pmp", "project", ("project_summary", "scope")),
        _Template("rfp", "all_rfp", ("background", "requested_services")),
        _Template("rft", "all_rft", ("background", "scope")),
    ),
    "programme_dirty": (
        _Template("pmp", "project", ("programme", "risks")),
        _Template("rfp", "all_rfp", ("programme",)),
        _Template("rft", "all_rft", ("programme",)),
    ),
    "cost_dirty": (
        _Template("cost_plan", "project", ("items", "totals")),
        _Template("pmp", "project", ("cost_planning",)),
    ),
    "consultants_dirty": (
        _Template("pmp", "project", ("consultants",)),
        _Template("rfp", "discipline", ("requested_services",)),
        _Template("consultant_register", "project", ("consultants",)),
        _Template("cost_plan", "project", ("consultant_fees",)),
    ),
    "ffe_dirty": (
        _Template("pmp", "project", ("ffe",)),
        _Template("rft", "package", ("scope", "materials")),
        _Template("cost_plan", "project", ("finishes", "ffe")),
    ),
    "approvals_dirty": (
        _Template("pmp", "project", ("planning_and_compliance", "risks")),
        _Template("rfp", "discipline", ("requested_services",)),
    ),
    "design_dirty": (
        _Template("pmp", "project", ("design_management", "risks")),
        _Template("rfp", "all_rfp", ("interfaces", "requested_services")),
        _Template("rft", "all_rft", ("interfaces", "design_responsibility")),
    ),
    "procurement_dirty": (
        _Template("pmp", "project", ("procurement_and_delivery",)),
        _Template("rfp", "all_rfp", ("submission_requirements",)),
        _Template("rft", "all_rft", ("submission_requirements",)),
    ),
}


def dirty_categories_for_profile_fields(
    fields: Iterable[str],
) -> tuple[DirtyCategory, ...]:
    dirty: list[DirtyCategory] = []
    for field in fields:
        dirty.extend(_PROFILE_DIRTY.get(field, ()))
    return tuple(dict.fromkeys(dirty))


def dirty_categories_for_block_sections(
    section_ids: Iterable[str],
) -> tuple[DirtyCategory, ...]:
    mapping: dict[str, tuple[DirtyCategory, ...]] = {
        "snapshot": ("scope_dirty",),
        "scope-client-requirements": ("scope_dirty",),
        "ffe-schedule": ("ffe_dirty",),
        "consultants": ("consultants_dirty",),
        "compliance-approvals": ("approvals_dirty",),
        "programme": ("programme_dirty",),
        "cost-budget": ("cost_dirty",),
        "procurement-delivery": ("procurement_dirty",),
        "risks": ("design_dirty", "approvals_dirty", "programme_dirty"),
    }
    dirty: list[DirtyCategory] = []
    for section_id in section_ids:
        dirty.extend(mapping.get(section_id, ()))
    return tuple(dict.fromkeys(dirty))


def affected_artefacts(
    dirty_categories: Iterable[DirtyCategory],
) -> tuple[AffectedArtefact, ...]:
    """Backward-compatible expansion using unresolved selector templates."""
    return resolve_concrete_affected(dirty_categories)


def resolve_concrete_affected(
    dirty_categories: Iterable[DirtyCategory],
    *,
    source_kind: str | None = None,
    object_id: str | None = None,
    previous_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    procurement_requests: Sequence[dict[str, Any]] = (),
    cost_items: Sequence[dict[str, Any]] = (),
    pmp_blocks: Sequence[dict[str, Any]] = (),
) -> tuple[AffectedArtefact, ...]:
    discipline_slug = _discipline_slug(source_kind, object_id, new_value or previous_value)
    package_slug = _package_slug(source_kind, object_id, new_value or previous_value)
    shared_key = (
        f"{source_kind}:{object_id}" if source_kind and object_id else None
    )
    old_name = _name_from(previous_value)
    new_name = _name_from(new_value)
    has_reference_patch = bool(old_name and new_name and old_name != new_name)

    affected: list[AffectedArtefact] = []
    seen: set[tuple[str, str | None, str | None, tuple[str, ...]]] = set()

    for category in dirty_categories:
        if source_kind == "ffe_item" and category == "cost_dirty":
            # FFE already targets finishes/ffe cost rows via ffe_dirty.
            continue
        if source_kind == "consultant" and category == "cost_dirty":
            continue
        for template in _DIRTY_TEMPLATES[category]:
            if template.selector_kind == "discipline" and not discipline_slug:
                continue
            if template.selector_kind == "package" and not package_slug:
                continue
            if (
                template.selector_kind in {"all_rfp", "all_rft"}
                and source_kind in {"consultant", "ffe_item"}
            ):
                # Source-scoped shared-object changes must not fan out to every
                # RFP/RFT; only the matching discipline/package templates apply.
                continue

            selector = _build_selector(
                template,
                discipline_slug=discipline_slug,
                package_slug=package_slug,
                shared_object_key=shared_key,
                procurement_requests=procurement_requests,
                cost_items=cost_items,
                pmp_blocks=pmp_blocks,
                old_name=old_name,
            )
            if template.selector_kind == "discipline" and selector.discipline_slug:
                if (
                    procurement_requests
                    and selector.procurement_request_id is None
                    and source_kind == "consultant"
                ):
                    # Keep the concrete discipline target even when no RFP exists yet.
                    pass
            if template.selector_kind == "package" and selector.package_slug:
                if (
                    procurement_requests
                    and selector.procurement_request_id is None
                    and source_kind == "ffe_item"
                ):
                    pass

            key = (
                template.artefact_type,
                selector.discipline_slug,
                selector.package_slug,
                template.blocks,
            )
            if key in seen:
                continue
            seen.add(key)
            update_mode: Literal["deterministic_reference", "selective_refresh"] = (
                "deterministic_reference"
                if has_reference_patch
                and template.artefact_type
                in {"pmp", "rfp", "rft", "consultant_register", "cost_plan"}
                else "selective_refresh"
            )
            affected.append(
                AffectedArtefact(
                    artefact_type=template.artefact_type,
                    selector=selector,
                    blocks=template.blocks,
                    update_mode=update_mode,
                )
            )
    return tuple(affected)


def mark_project_dirty(project: Project, categories: Iterable[DirtyCategory]) -> None:
    mark_project_dirty_from_change(project, categories=tuple(categories))


def mark_project_dirty_from_change(
    project: Project,
    *,
    categories: Iterable[DirtyCategory],
    source_kind: str | None = None,
    object_id: str | None = None,
    revision: int | None = None,
    previous_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    artefacts: Sequence[AffectedArtefact] | None = None,
) -> None:
    additions = tuple(categories)
    if not additions:
        return
    metadata = dict(project.project_metadata or {})
    existing = metadata.get("dirty_categories")
    current = (
        [value for value in existing if isinstance(value, str)]
        if isinstance(existing, list)
        else []
    )
    metadata["dirty_categories"] = list(dict.fromkeys([*current, *additions]))

    resolved = tuple(artefacts) if artefacts is not None else resolve_concrete_affected(
        additions,
        source_kind=source_kind,
        object_id=object_id,
        previous_value=previous_value,
        new_value=new_value,
    )
    metadata["affected_artefacts"] = [
        item.model_dump(mode="json")
        for item in _merge_affected(
            metadata.get("affected_artefacts"),
            resolved,
        )
    ]

    if source_kind and object_id:
        offers = [
            item
            for item in _load_offers(metadata)
            if not (
                item.source.kind == source_kind
                and item.source.object_id == object_id
            )
        ]
        # Only open a reviewable offer once a concrete prior value exists.
        if previous_value is not None:
            offer = DependencyUpdateOffer(
                id=_offer_id(
                    source_kind, object_id, additions, previous_value, new_value
                ),
                category=additions[0],
                source=DirtyChangeSource(
                    kind=source_kind,
                    object_id=object_id,
                    revision=revision,
                ),
                artefacts=resolved,
                reference_patch=_reference_patch(previous_value, new_value),
            )
            offers.append(offer)
        if offers:
            metadata["dependency_offers"] = [
                item.model_dump(mode="json") for item in offers
            ]
        else:
            metadata.pop("dependency_offers", None)

    project.project_metadata = metadata


def clear_project_dirty(project: Project, categories: Iterable[DirtyCategory]) -> None:
    removing = set(categories)
    metadata = dict(project.project_metadata or {})
    current = metadata.get("dirty_categories")
    remaining = (
        [value for value in current if isinstance(value, str) and value not in removing]
        if isinstance(current, list)
        else []
    )
    offers = [
        offer
        for offer in _load_offers(metadata)
        if offer.category not in removing
    ]
    if remaining:
        metadata["dirty_categories"] = remaining
        metadata["affected_artefacts"] = [
            item.model_dump(mode="json")
            for item in resolve_concrete_affected(remaining)
        ]
    else:
        metadata.pop("dirty_categories", None)
        metadata.pop("affected_artefacts", None)
    if offers:
        metadata["dependency_offers"] = [
            item.model_dump(mode="json") for item in offers
        ]
    else:
        metadata.pop("dependency_offers", None)
    project.project_metadata = metadata


def list_dependency_offers(project: Project) -> list[DependencyUpdateOffer]:
    return _load_offers(dict(project.project_metadata or {}))


def get_dependency_offer(
    project: Project, offer_id: str
) -> DependencyUpdateOffer | None:
    for offer in list_dependency_offers(project):
        if offer.id == offer_id:
            return offer
    return None


def clear_consumed_dependency_entries(
    project: Project,
    *,
    offer_id: str,
    artefact_types: Sequence[str],
) -> DependencyUpdateOffer:
    metadata = dict(project.project_metadata or {})
    offers = _load_offers(metadata)
    target = next((item for item in offers if item.id == offer_id), None)
    if target is None:
        raise LookupError(f"dependency offer not found: {offer_id}")
    removing = set(artefact_types)
    remaining_artefacts = tuple(
        item for item in target.artefacts if item.artefact_type not in removing
    )
    offers = [item for item in offers if item.id != offer_id]
    if remaining_artefacts:
        updated = target.model_copy(
            update={
                "artefacts": remaining_artefacts,
                "status": "partial",
            }
        )
        offers.append(updated)
        result = updated
    else:
        result = target.model_copy(update={"artefacts": (), "status": "partial"})

    _write_offers_and_dirty(project, metadata, offers)
    return result


def reject_dependency_offer(
    project: Project,
    *,
    offer_id: str,
    artefact_types: Sequence[str] | None = None,
) -> None:
    metadata = dict(project.project_metadata or {})
    offers = _load_offers(metadata)
    if not any(item.id == offer_id for item in offers):
        raise LookupError(f"dependency offer not found: {offer_id}")
    if artefact_types is None:
        offers = [item for item in offers if item.id != offer_id]
        _write_offers_and_dirty(project, metadata, offers)
        return
    clear_consumed_dependency_entries(
        project,
        offer_id=offer_id,
        artefact_types=artefact_types,
    )


def apply_deterministic_reference_update(
    markdown: str,
    *,
    metadata: dict[str, Any],
    block_ids: Sequence[str],
    old_text: str,
    new_text: str,
) -> tuple[str, tuple[str, ...]]:
    if not old_text or old_text == new_text:
        return markdown, ()
    changed: list[str] = []
    current = markdown
    for block_id in block_ids:
        blocks = {block.id: block for block in markdown_blocks(current) if block.id}
        block = blocks.get(block_id)
        if block is None:
            continue
        raw = metadata.get(block_id)
        if isinstance(raw, dict) and raw.get("user_protected"):
            continue
        segment = current[block.start : block.end]
        if old_text not in segment:
            continue
        current = (
            current[: block.start]
            + segment.replace(old_text, new_text, 1)
            + current[block.end :]
        )
        changed.append(block_id)
    return current, tuple(changed)


def apply_deterministic_text_replace(text: str, *, old_text: str, new_text: str) -> str:
    if not old_text or old_text == new_text:
        return text
    return text.replace(old_text, new_text)


def _write_offers_and_dirty(
    project: Project,
    metadata: dict[str, Any],
    offers: list[DependencyUpdateOffer],
) -> None:
    if offers:
        metadata["dependency_offers"] = [
            item.model_dump(mode="json") for item in offers
        ]
        metadata["dirty_categories"] = list(
            dict.fromkeys(item.category for item in offers)
        )
        merged: list[AffectedArtefact] = []
        for offer in offers:
            merged.extend(offer.artefacts)
        metadata["affected_artefacts"] = [
            item.model_dump(mode="json") for item in _dedupe_affected(merged)
        ]
    else:
        metadata.pop("dependency_offers", None)
        metadata.pop("dirty_categories", None)
        metadata.pop("affected_artefacts", None)
    project.project_metadata = metadata


def _load_offers(metadata: dict[str, Any]) -> list[DependencyUpdateOffer]:
    raw = metadata.get("dependency_offers")
    if not isinstance(raw, list):
        return []
    offers: list[DependencyUpdateOffer] = []
    for item in raw:
        if isinstance(item, dict):
            offers.append(DependencyUpdateOffer.model_validate(item))
    return offers


def _merge_affected(
    existing: Any,
    additions: Sequence[AffectedArtefact],
) -> tuple[AffectedArtefact, ...]:
    current: list[AffectedArtefact] = []
    if isinstance(existing, list):
        for item in existing:
            if isinstance(item, dict):
                # Migrate legacy placeholder selector strings.
                selector = item.get("selector")
                if isinstance(selector, str) or selector is None:
                    item = {
                        **item,
                        "selector": _legacy_selector(item),
                    }
                current.append(AffectedArtefact.model_validate(item))
    current.extend(additions)
    return _dedupe_affected(current)


def _dedupe_affected(
    items: Sequence[AffectedArtefact],
) -> tuple[AffectedArtefact, ...]:
    seen: set[tuple[str, str | None, str | None, tuple[str, ...]]] = set()
    result: list[AffectedArtefact] = []
    for item in items:
        key = (
            item.artefact_type,
            item.selector.discipline_slug,
            item.selector.package_slug,
            item.blocks,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return tuple(result)


def _legacy_selector(item: dict[str, Any]) -> dict[str, Any]:
    selector = item.get("selector")
    if selector == "affected_discipline":
        return {"discipline_slug": None}
    if selector == "affected_package":
        return {"package_slug": None}
    if selector == "*":
        return {}
    return {}


def _build_selector(
    template: _Template,
    *,
    discipline_slug: str | None,
    package_slug: str | None,
    shared_object_key: str | None,
    procurement_requests: Sequence[dict[str, Any]],
    cost_items: Sequence[dict[str, Any]],
    pmp_blocks: Sequence[dict[str, Any]],
    old_name: str | None,
) -> ArtefactSelector:
    section_ids = tuple(
        _SECTION_BY_DIRTY_BLOCK[block]
        for block in template.blocks
        if block in _SECTION_BY_DIRTY_BLOCK
    )
    selector = ArtefactSelector(
        shared_object_key=shared_object_key,
        section_ids=section_ids,
    )
    if template.selector_kind == "discipline" or (
        template.artefact_type == "rfp" and discipline_slug
    ):
        match = _match_request(
            procurement_requests,
            kind_prefix="consultant_rfp",
            slug=discipline_slug,
        )
        selector = selector.model_copy(
            update={
                "discipline_slug": discipline_slug,
                "procurement_request_id": match.get("id") if match else None,
                "draft_id": match.get("current_draft_artifact_id") if match else None,
                "draft_workflow_type": (
                    f"consultant_procurement_{discipline_slug}"
                    if discipline_slug
                    else None
                ),
            }
        )
    elif template.selector_kind == "package" or (
        template.artefact_type == "rft" and package_slug
    ):
        match = _match_request(
            procurement_requests,
            kind_prefix="trade_",
            slug=package_slug,
        )
        selector = selector.model_copy(
            update={
                "package_slug": package_slug,
                "procurement_request_id": match.get("id") if match else None,
                "draft_id": match.get("current_draft_artifact_id") if match else None,
                "draft_workflow_type": (
                    f"trade_rft_{package_slug}" if package_slug else None
                ),
            }
        )
    elif template.artefact_type in {"pmp", "consultant_register"}:
        selector = selector.model_copy(
            update={
                "draft_workflow_type": "create_pmp",
                "block_ids": _matching_pmp_block_ids(
                    pmp_blocks,
                    section_ids=section_ids,
                    old_name=old_name,
                    artefact_type=template.artefact_type,
                    blocks=template.blocks,
                ),
            }
        )
    elif template.artefact_type == "cost_plan":
        selector = selector.model_copy(
            update={
                "cost_item_keys": _matching_cost_item_keys(
                    cost_items,
                    blocks=template.blocks,
                    discipline_slug=discipline_slug,
                    package_slug=package_slug,
                    old_name=old_name,
                ),
            }
        )
    return selector


def _matching_pmp_block_ids(
    pmp_blocks: Sequence[dict[str, Any]],
    *,
    section_ids: tuple[str, ...],
    old_name: str | None,
    artefact_type: ArtefactType,
    blocks: tuple[str, ...],
) -> tuple[str, ...]:
    if not pmp_blocks:
        return ()
    wanted_sections = set(section_ids)
    if "ffe" in blocks or "ffe-schedule" in blocks:
        wanted_sections.add("ffe-schedule")
    matches: list[str] = []
    for block in pmp_blocks:
        section_id = str(block.get("section_id") or "")
        content = str(block.get("content") or "")
        block_id = str(block.get("id") or "")
        if not block_id or section_id not in wanted_sections:
            continue
        if artefact_type == "consultant_register":
            matches.append(block_id)
            continue
        if old_name and old_name in content:
            matches.append(block_id)
        elif not old_name and (
            section_id in {"ffe-schedule", "consultants"}
            or "ffe" in content.lower()
        ):
            matches.append(block_id)
        elif "ffe" in blocks and (
            section_id == "ffe-schedule" or "ffe" in content.lower()
        ):
            matches.append(block_id)
    return tuple(dict.fromkeys(matches))


def _matching_cost_item_keys(
    cost_items: Sequence[dict[str, Any]],
    *,
    blocks: tuple[str, ...],
    discipline_slug: str | None,
    package_slug: str | None,
    old_name: str | None,
) -> tuple[str, ...]:
    if not cost_items:
        return ()
    keys: list[str] = []
    for item in cost_items:
        item_key = str(item.get("item_key") or "")
        category = str(item.get("category") or "")
        label = str(item.get("item") or "")
        if not item_key:
            continue
        if "consultant_fees" in blocks or (
            discipline_slug and "Consultants" in category
        ):
            if discipline_slug and (
                discipline_slug in item_key
                or (old_name and old_name in label)
                or _slug_tokens(discipline_slug) & _slug_tokens(item_key + " " + label)
            ):
                keys.append(item_key)
                continue
        if "finishes" in blocks or "ffe" in blocks:
            if package_slug and (
                package_slug in item_key
                or package_slug.replace("_", "-") in item_key
                or (old_name and old_name in label)
            ):
                keys.append(item_key)
                continue
            if "Finishes" in category and package_slug:
                if package_slug in item_key or package_slug in label.lower():
                    keys.append(item_key)
    return tuple(dict.fromkeys(keys))


def _match_request(
    requests: Sequence[dict[str, Any]],
    *,
    kind_prefix: str,
    slug: str | None,
) -> dict[str, Any] | None:
    if not slug:
        return None
    for request in requests:
        kind = str(request.get("kind") or "")
        target_slug = str(request.get("target_slug") or "")
        if not kind.startswith(kind_prefix.replace("trade_", "trade")) and not (
            kind_prefix == "trade_" and kind.startswith("trade_")
        ):
            if kind_prefix == "consultant_rfp" and kind != "consultant_rfp":
                continue
            if kind_prefix == "trade_" and not kind.startswith("trade_"):
                continue
        if kind_prefix == "consultant_rfp" and kind != "consultant_rfp":
            continue
        if target_slug == slug:
            return request
    return None


def _discipline_slug(
    source_kind: str | None,
    object_id: str | None,
    value: dict[str, Any] | None,
) -> str | None:
    if source_kind != "consultant":
        return None
    candidates: list[str] = []
    if object_id:
        candidates.append(object_id)
    if isinstance(value, dict):
        for key in ("discipline", "slug"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                candidates.append(candidate.strip())
    for raw in candidates:
        catalog = _catalog_discipline_slug(raw)
        if catalog:
            return catalog
    if not candidates:
        return None
    try:
        from app.workflows.consultant_procurement import normalise_discipline

        return normalise_discipline(candidates[0]).slug
    except Exception:
        return _slugify(candidates[0])


def _catalog_discipline_slug(raw: str) -> str | None:
    try:
        from app.workflows.consultant_procurement import DISCIPLINE_PROFILES
    except Exception:
        return None
    token = _slugify(raw)
    if not token:
        return None
    for profile in DISCIPLINE_PROFILES.values():
        if profile.slug == token or token in profile.slug.split("_"):
            return profile.slug
    return None


def _package_slug(
    source_kind: str | None,
    object_id: str | None,
    value: dict[str, Any] | None,
) -> str | None:
    if source_kind not in {"ffe_item", "procurement_package"}:
        return None
    if isinstance(value, dict):
        raw = value.get("package") or value.get("slug") or object_id
    else:
        raw = object_id
    if not raw:
        return None
    return _slugify(str(raw))


def _name_from(value: dict[str, Any] | None) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("name", "firm", "label", "title"):
        raw = value.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def _reference_patch(
    previous_value: dict[str, Any] | None,
    new_value: dict[str, Any] | None,
) -> dict[str, str] | None:
    old_name = _name_from(previous_value)
    new_name = _name_from(new_value)
    if old_name and new_name and old_name != new_name:
        return {"from": old_name, "to": new_name}
    return None


def _offer_id(
    source_kind: str,
    object_id: str,
    categories: Sequence[DirtyCategory],
    previous_value: dict[str, Any] | None,
    new_value: dict[str, Any] | None,
) -> str:
    payload = "|".join(
        [
            source_kind,
            object_id,
            ",".join(categories),
            _name_from(previous_value) or "",
            _name_from(new_value) or "",
        ]
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
    return f"offer_{digest}"


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_") or "item"


def _slug_tokens(value: str) -> set[str]:
    return {token for token in _slugify(value).split("_") if len(token) > 2}
