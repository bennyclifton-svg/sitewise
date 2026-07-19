from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.database.session import get_session_factory
from app.database.workspace_files import get_workspace_file_by_path
from app.workflows.consultant_procurement import (
    is_consultant_procurement_workflow,
    sync_consultant_procurement_draft_workspace,
)
from app.workflows.create_cost_plan import (
    is_cost_plan_workflow,
    sync_cost_plan_revision_artifacts,
)
from app.workflows.create_pmp import is_pmp_workflow, sync_pmp_draft_workspace


async def backfill(*, apply: bool) -> dict[str, int]:
    counts = {"missing": 0, "repaired": 0, "unsupported": 0}
    async with get_session_factory()() as session:
        rows = (
            await session.execute(
                select(DraftArtifact, Project)
                .join(Project, Project.id == DraftArtifact.project_id)
                .order_by(
                    DraftArtifact.project_id,
                    DraftArtifact.workflow_type,
                    DraftArtifact.version,
                )
            )
        ).all()
        for draft, project in rows:
            existing = await get_workspace_file_by_path(
                session,
                project_id=project.id,
                workspace_path=draft.workspace_path,
            )
            if existing is not None:
                continue
            counts["missing"] += 1
            if not apply:
                continue
            if is_pmp_workflow(draft.workflow_type):
                await sync_pmp_draft_workspace(session, project=project, draft=draft)
            elif is_cost_plan_workflow(draft.workflow_type):
                await sync_cost_plan_revision_artifacts(
                    session, project=project, draft=draft
                )
            elif is_consultant_procurement_workflow(draft.workflow_type):
                await sync_consultant_procurement_draft_workspace(
                    session, project=project, draft=draft
                )
            else:
                counts["unsupported"] += 1
                continue
            counts["repaired"] += 1
        if apply:
            await session.commit()
        else:
            await session.rollback()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill missing workspace exports. Dry-run is the default."
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(asyncio.run(backfill(apply=args.apply)))


if __name__ == "__main__":
    main()
