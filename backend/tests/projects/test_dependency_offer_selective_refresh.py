"""F7: dependency offer accept runs selective narrative refresh."""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.database.project import Project
from app.projects.dependencies import (
    AffectedArtefact,
    ArtefactSelector,
    mark_project_dirty_from_change,
    list_dependency_offers,
)
from app.projects.dependency_offers import accept_dependency_offer


def test_accept_selective_refresh_invokes_runner_for_selected_artefact() -> None:
    project = Project(
        id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
        phase="brief-planning",
        project_metadata={},
    )
    target = AffectedArtefact(
        artefact_type="pmp",
        selector=ArtefactSelector(
            draft_id=str(uuid.uuid4()),
            section_ids=("consultants",),
        ),
        blocks=("consultants",),
        update_mode="selective_refresh",
    )
    mark_project_dirty_from_change(
        project,
        categories=("consultants_dirty",),
        source_kind="consultant",
        object_id="hydraulic",
        previous_value={"name": "ABC Engineering"},
        new_value={"name": "Fluid Design"},
        artefacts=(target,),
    )
    offer = list_dependency_offers(project)[0]
    calls: list[AffectedArtefact] = []

    async def runner(session, **kwargs):
        del session
        calls.append(kwargs["target"])
        return True

    result = asyncio.run(
        accept_dependency_offer(
            SimpleNamespace(),
            project=project,
            offer_id=offer.id,
            artefact_types=["pmp"],
            author_user_id=project.owner_user_id,
            run_selective_refresh=runner,
        )
    )

    assert result.updated_artefact_types == ("pmp",)
    assert len(calls) == 1
    assert calls[0].selector.section_ids == ("consultants",)
    assert list_dependency_offers(project) == []
