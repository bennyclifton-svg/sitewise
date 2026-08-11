"""Baseline-aware selective refresh for PMP, RFP and RFT narrative artefacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Sequence

from app.projects.artefact_blocks import (
    IncrementalBlockProposal,
    IncrementalMergeResult,
    block_input_hash,
    markdown_blocks,
    merge_incremental_block_updates,
    reconcile_regenerated_blocks,
)
from app.sitewise.section_contracts import section_id_for_heading


@dataclass(frozen=True, slots=True)
class SelectiveRefreshPlan:
    refresh_input_hash: str
    skip: bool
    affected_section_ids: tuple[str, ...]


def compute_refresh_input_hash(
    *,
    context_version: int,
    source_version: str,
    seed_version: str,
    artefact_type: str,
    affected_section_ids: Sequence[str] = (),
) -> str:
    return block_input_hash(
        context_version=context_version,
        source_version=source_version,
        seed_version=seed_version,
        inputs={
            "artefact_type": artefact_type,
            "affected_sections": list(affected_section_ids),
        },
    )


def prior_refresh_input_hash(provenance: dict[str, Any] | None) -> str | None:
    if not isinstance(provenance, dict):
        return None
    incremental = provenance.get("incremental_update")
    if isinstance(incremental, dict):
        value = incremental.get("input_hash")
        if isinstance(value, str) and value:
            return value
    brief = provenance.get("generation_brief")
    if isinstance(brief, dict):
        fingerprint = brief.get("input_fingerprint")
        if isinstance(fingerprint, str) and fingerprint:
            return fingerprint
    return None


def plan_selective_refresh(
    provenance: dict[str, Any] | None,
    *,
    context_version: int,
    source_version: str,
    seed_version: str,
    artefact_type: str,
    affected_section_ids: Sequence[str] = (),
) -> SelectiveRefreshPlan:
    refresh_hash = compute_refresh_input_hash(
        context_version=context_version,
        source_version=source_version,
        seed_version=seed_version,
        artefact_type=artefact_type,
        affected_section_ids=affected_section_ids,
    )
    prior = prior_refresh_input_hash(provenance)
    return SelectiveRefreshPlan(
        refresh_input_hash=refresh_hash,
        skip=prior is not None and prior == refresh_hash,
        affected_section_ids=tuple(affected_section_ids),
    )


def stamp_block_versions(
    metadata: dict[str, Any],
    *,
    context_version: int,
    source_version: str,
    seed_version: str,
    generation_version: str | None = None,
    section_input_hashes: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    stamped: dict[str, dict[str, Any]] = {}
    for block_id, raw in metadata.items():
        if not isinstance(raw, dict):
            continue
        copied = dict(raw)
        copied["context_version"] = context_version
        copied["source_version"] = source_version
        copied["seed_version"] = seed_version
        if generation_version is not None:
            copied["generation_version"] = generation_version
        if section_input_hashes and block_id in section_input_hashes:
            copied["input_hash"] = section_input_hashes[block_id]
        stamped[block_id] = copied
    return stamped


def build_incremental_audit(
    result: IncrementalMergeResult,
    *,
    refresh_input_hash: str,
) -> dict[str, Any]:
    proposed_delete = tuple(
        block_id
        for block_id, raw in result.metadata.items()
        if isinstance(raw, dict) and raw.get("status") == "propose_delete"
    )
    return {
        "updated": list(result.updated),
        "preserved": list(result.preserved),
        "conflicts": list(result.conflicts),
        "proposed_delete": list(proposed_delete),
        "input_hash": refresh_input_hash,
    }


def section_id_at(markdown: str, offset: int, *, work_type: str | None = None) -> str | None:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", markdown[:offset]))
    if not matches:
        return None
    heading = matches[-1].group(1).strip()
    return section_id_for_heading(heading, work_type=work_type) or heading.casefold()


def apply_selective_section_refresh(
    baseline_markdown: str,
    baseline_metadata: dict[str, Any],
    regenerated_markdown: str,
    *,
    affected_section_ids: Sequence[str],
    context_version: int,
    source_version: str,
    seed_version: str,
    artefact_type: str,
    generation_version: str,
    work_type: str | None = None,
    now: datetime | None = None,
) -> IncrementalMergeResult:
    """Refresh only blocks under affected sections; keep others byte-identical."""
    timestamp = now or datetime.now(UTC)
    wanted = {value for value in affected_section_ids}
    if not wanted:
        reconciled = reconcile_regenerated_blocks(
            baseline_markdown,
            baseline_metadata,
            regenerated_markdown,
            generation_input_hash=compute_refresh_input_hash(
                context_version=context_version,
                source_version=source_version,
                seed_version=seed_version,
                artefact_type=artefact_type,
            ),
            generation_version=generation_version,
            now=timestamp,
        )
        stamped = stamp_block_versions(
            reconciled.metadata,
            context_version=context_version,
            source_version=source_version,
            seed_version=seed_version,
            generation_version=generation_version,
        )
        return IncrementalMergeResult(
            markdown=reconciled.markdown,
            metadata=stamped,
            updated=reconciled.updated,
            preserved=reconciled.preserved,
            conflicts=reconciled.conflicts,
        )

    section_hashes: dict[str, str] = {}
    for section_id in wanted:
        section_hashes[section_id] = block_input_hash(
            context_version=context_version,
            source_version=source_version,
            seed_version=seed_version,
            inputs={"artefact_type": artefact_type, "section_id": section_id},
        )

    regenerated_by_id = {
        block.id: block
        for block in markdown_blocks(regenerated_markdown)
        if block.id
        and section_id_at(regenerated_markdown, block.start, work_type=work_type)
        in wanted
    }
    proposals: list[IncrementalBlockProposal] = []
    block_hashes: dict[str, str] = {}
    for block in markdown_blocks(baseline_markdown):
        if block.id is None:
            continue
        section_id = section_id_at(baseline_markdown, block.start, work_type=work_type)
        if section_id not in wanted:
            continue
        input_hash = section_hashes[section_id]
        block_hashes[block.id] = input_hash
        proposed = regenerated_by_id.get(block.id)
        proposals.append(
            IncrementalBlockProposal(
                block_id=block.id,
                content=proposed.content if proposed is not None else None,
                input_hash=input_hash,
            )
        )

    # New AI blocks that appear only in the regenerated affected sections.
    baseline_ids = {block.id for block in markdown_blocks(baseline_markdown) if block.id}
    for block_id, block in regenerated_by_id.items():
        if block_id in baseline_ids:
            continue
        section_id = section_id_at(
            regenerated_markdown, block.start, work_type=work_type
        )
        if section_id is None or section_id not in wanted:
            continue
        input_hash = section_hashes[section_id]
        block_hashes[block_id] = input_hash
        # merge_incremental_block_updates cannot insert unknown ids; splice via
        # full reconcile when new blocks appear.
        return _reconcile_with_versions(
            baseline_markdown,
            baseline_metadata,
            regenerated_markdown,
            context_version=context_version,
            source_version=source_version,
            seed_version=seed_version,
            artefact_type=artefact_type,
            affected_section_ids=affected_section_ids,
            generation_version=generation_version,
            now=timestamp,
        )

    merged = merge_incremental_block_updates(
        baseline_markdown,
        baseline_metadata,
        proposals,
        now=timestamp,
    )
    metadata = {
        key: dict(value)
        for key, value in merged.metadata.items()
        if isinstance(value, dict)
    }
    affected_meta = {
        block_id: metadata[block_id]
        for block_id in block_hashes
        if block_id in metadata
    }
    stamped_affected = stamp_block_versions(
        affected_meta,
        context_version=context_version,
        source_version=source_version,
        seed_version=seed_version,
        generation_version=generation_version,
        section_input_hashes=block_hashes,
    )
    metadata.update(stamped_affected)
    return IncrementalMergeResult(
        markdown=merged.markdown,
        metadata=metadata,
        updated=merged.updated,
        preserved=merged.preserved,
        conflicts=merged.conflicts,
    )


def apply_document_refresh(
    baseline_markdown: str,
    baseline_metadata: dict[str, Any],
    regenerated_markdown: str,
    *,
    context_version: int,
    source_version: str,
    seed_version: str,
    artefact_type: str,
    generation_version: str,
    affected_section_ids: Sequence[str] = (),
    work_type: str | None = None,
    now: datetime | None = None,
) -> IncrementalMergeResult:
    """Reconcile a regenerated narrative, optionally scoped to section ids."""
    if affected_section_ids:
        return apply_selective_section_refresh(
            baseline_markdown,
            baseline_metadata,
            regenerated_markdown,
            affected_section_ids=affected_section_ids,
            context_version=context_version,
            source_version=source_version,
            seed_version=seed_version,
            artefact_type=artefact_type,
            generation_version=generation_version,
            work_type=work_type,
            now=now,
        )
    return _reconcile_with_versions(
        baseline_markdown,
        baseline_metadata,
        regenerated_markdown,
        context_version=context_version,
        source_version=source_version,
        seed_version=seed_version,
        artefact_type=artefact_type,
        affected_section_ids=(),
        generation_version=generation_version,
        now=now or datetime.now(UTC),
    )


def _reconcile_with_versions(
    baseline_markdown: str,
    baseline_metadata: dict[str, Any],
    regenerated_markdown: str,
    *,
    context_version: int,
    source_version: str,
    seed_version: str,
    artefact_type: str,
    affected_section_ids: Sequence[str],
    generation_version: str,
    now: datetime,
) -> IncrementalMergeResult:
    generation_input_hash = compute_refresh_input_hash(
        context_version=context_version,
        source_version=source_version,
        seed_version=seed_version,
        artefact_type=artefact_type,
        affected_section_ids=affected_section_ids,
    )
    reconciled = reconcile_regenerated_blocks(
        baseline_markdown,
        baseline_metadata,
        regenerated_markdown,
        generation_input_hash=generation_input_hash,
        generation_version=generation_version,
        now=now,
    )
    stamped = stamp_block_versions(
        reconciled.metadata,
        context_version=context_version,
        source_version=source_version,
        seed_version=seed_version,
        generation_version=generation_version,
    )
    return IncrementalMergeResult(
        markdown=reconciled.markdown,
        metadata=stamped,
        updated=reconciled.updated,
        preserved=reconciled.preserved,
        conflicts=reconciled.conflicts,
    )

