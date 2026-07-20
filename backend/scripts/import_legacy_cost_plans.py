from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.cost_plan.import_legacy import import_legacy_draft
from app.database.draft_artifact import DraftArtifact
from app.database.session import get_session_factory


async def run(*, apply: bool) -> dict[str, object]:
    results: list[dict[str, object]] = []
    async with get_session_factory()() as session:
        drafts = list(
            (
                await session.execute(
                    select(DraftArtifact)
                    .where(
                        DraftArtifact.workflow_type == "create_cost_plan",
                        DraftArtifact.status == "accepted",
                    )
                    .order_by(DraftArtifact.project_id, DraftArtifact.version)
                )
            ).scalars()
        )
        for draft in drafts:
            result = await import_legacy_draft(session, draft=draft, apply=apply)
            results.append(
                {
                    "draft_id": str(draft.id),
                    "version": draft.version,
                    "item_count": len(result.items),
                    "parsed_total": str(result.parsed_budget_total),
                    "source_total": str(result.source_budget_total)
                    if result.source_budget_total is not None
                    else None,
                    "warnings": list(result.warnings),
                    "applied": result.applied,
                }
            )
        if apply:
            await session.commit()
        else:
            await session.rollback()
    return {"mode": "apply" if apply else "dry-run", "drafts": results}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import accepted Markdown Cost Plans into canonical typed state. Dry-run is the default."
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(asyncio.run(run(apply=args.apply)))


if __name__ == "__main__":
    main()
