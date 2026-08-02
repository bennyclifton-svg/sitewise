"""Create slim request-register rows for legacy consultant RFP and contractor EOI drafts.

Run a dry report first, then apply the changes:

    uv run python scripts/backfill_procurement_requests.py
    uv run python scripts/backfill_procurement_requests.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.database.models  # noqa: F401
from app.database.draft_artifact import DraftArtifact
from app.database.procurement_request import ProcurementRequest
from app.database.session import get_session_factory
from app.procurement.requests import (
    attach_current_draft,
    create_procurement_request,
    normalise_target_name,
    request_kind_for_workflow,
)

LEGACY_WORKFLOW_PREFIXES = ("consultant_procurement_", "contractor_eoi_")
_TARGET_METADATA_KEYS = ("discipline", "package", "target_name", "target")


@dataclass(slots=True)
class BackfillReport:
    scanned_drafts: int = 0
    lineages: int = 0
    created: int = 0
    attached: int = 0
    skipped: int = 0
    conflicts: list[str] = field(default_factory=list)


def legacy_request_details(draft: DraftArtifact) -> tuple[str, str]:
    """Derive the trusted request identity without reading document body text."""
    kind = request_kind_for_workflow(draft.workflow_type)
    metadata = draft.provenance_metadata or {}
    for key in _TARGET_METADATA_KEYS:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return kind, " ".join(value.split())

    if kind == "consultant_rfp":
        suffix = draft.workflow_type.removeprefix("consultant_procurement_")
    else:
        suffix = draft.workflow_type.removeprefix("contractor_eoi_")
    return kind, suffix.replace("_", " ").strip() or "Main Works"


def latest_legacy_lineages(drafts: Iterable[DraftArtifact]) -> list[DraftArtifact]:
    """Keep the newest artefact for each project/workflow lineage."""
    latest: dict[tuple[object, str], DraftArtifact] = {}
    for draft in drafts:
        if not draft.workflow_type.startswith(LEGACY_WORKFLOW_PREFIXES):
            continue
        key = (draft.project_id, draft.workflow_type)
        current = latest.get(key)
        if current is None or draft.version > current.version:
            latest[key] = draft
    return list(latest.values())


async def _legacy_drafts(session: AsyncSession) -> list[DraftArtifact]:
    result = await session.execute(
        select(DraftArtifact)
        .where(
            DraftArtifact.workflow_type.like("consultant_procurement_%")
            | DraftArtifact.workflow_type.like("contractor_eoi_%")
        )
        .order_by(
            DraftArtifact.project_id.asc(),
            DraftArtifact.workflow_type.asc(),
            DraftArtifact.version.desc(),
        )
    )
    return list(result.scalars())


async def backfill(session: AsyncSession, *, apply: bool) -> BackfillReport:
    drafts = await _legacy_drafts(session)
    lineages = latest_legacy_lineages(drafts)
    report = BackfillReport(scanned_drafts=len(drafts), lineages=len(lineages))

    for draft in lineages:
        kind, target_name = legacy_request_details(draft)
        _normalised_name, target_slug = normalise_target_name(target_name)
        existing_for_draft = await session.execute(
            select(ProcurementRequest).where(
                ProcurementRequest.project_id == draft.project_id,
                ProcurementRequest.current_draft_artifact_id == draft.id,
            )
        )
        if existing_for_draft.scalar_one_or_none() is not None:
            report.skipped += 1
            continue

        matching = await session.execute(
            select(ProcurementRequest)
            .where(
                ProcurementRequest.project_id == draft.project_id,
                ProcurementRequest.kind == kind,
                ProcurementRequest.target_slug == target_slug,
            )
            .order_by(ProcurementRequest.updated_at.desc())
        )
        requests = list(matching.scalars())
        if len(requests) > 1:
            report.conflicts.append(
                f"{draft.project_id}/{draft.workflow_type}: multiple matching request rows"
            )
            continue

        request = requests[0] if requests else None
        if request is not None and request.status != "draft":
            report.conflicts.append(
                f"{draft.project_id}/{draft.workflow_type}: matching request is {request.status}"
            )
            continue

        if not apply:
            if request is None:
                report.created += 1
            else:
                report.attached += 1
            continue

        if request is None:
            request = await create_procurement_request(
                session,
                project_id=draft.project_id,
                created_by_user_id=draft.author_user_id,
                kind=kind,
                target_name=target_name,
            )
            report.created += 1

        await attach_current_draft(session, request=request, draft=draft)
        metadata = dict(draft.provenance_metadata or {})
        metadata["procurement_request_id"] = str(request.id)
        metadata["procurement_request_kind"] = kind
        draft.provenance_metadata = metadata
        await session.flush()
        report.attached += 1

    return report


async def _run(apply: bool) -> BackfillReport:
    session_factory = get_session_factory()
    async with session_factory() as session:
        report = await backfill(session, apply=apply)
        if apply:
            await session.commit()
        else:
            await session.rollback()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write request rows; omit for a rollback-only report",
    )
    args = parser.parse_args()
    print(json.dumps(asdict(asyncio.run(_run(args.apply))), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
