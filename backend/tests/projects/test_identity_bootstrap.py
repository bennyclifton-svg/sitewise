from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.project import Project
from app.database.project_profile_proposal import ProjectProfileProposal
from app.projects.identity_bootstrap import bootstrap_identity_from_document
from app.projects.profile import read_profile


def _project(**overrides) -> Project:
    values = {
        "id": uuid.uuid4(),
        "owner_user_id": uuid.uuid4(),
        "slug": "walsh-2",
        "title": "Walsh 2",
        "workspace_path": "04-projects/walsh-2",
        "phase": "brief-planning",
        "archetype": None,
        "building_class": "residential",
        "work_type": "refurb",
        "user_role": "architect-pm",
        "state": "NSW",
        "profile_revision": 1,
        "event_sequence": 0,
        "status": "active",
        "project_metadata": {"taxonomy": {"subclasses": ["house"]}},
    }
    values.update(overrides)
    return Project(**values)


def _flush_assigns_ids(session: AsyncMock) -> None:
    added: list[object] = []

    def add(obj: object) -> None:
        added.append(obj)

    async def flush() -> None:
        for obj in added:
            if getattr(obj, "id", None) is None and hasattr(obj, "id"):
                obj.id = uuid.uuid4()  # type: ignore[attr-defined]
            now = datetime.now(UTC)
            if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
                obj.created_at = now  # type: ignore[attr-defined]
            if hasattr(obj, "updated_at"):
                obj.updated_at = now  # type: ignore[attr-defined]

    async def get(_model: object, key: object, **_kwargs: object) -> object | None:
        for obj in reversed(added):
            if getattr(obj, "id", None) == key:
                return obj
        return None

    session.add.side_effect = add
    session.flush.side_effect = flush
    session.get.side_effect = get


def test_high_confidence_address_auto_applies_when_empty() -> None:
    project = _project()
    source_id = uuid.uuid4()
    session = AsyncMock()
    session.add = MagicMock()
    _flush_assigns_ids(session)

    text = (
        "Project brief — proposed new dwelling at "
        "42 Hargrave Street, Paddington NSW 2021"
    )

    with (
        patch(
            "app.projects.identity_bootstrap.list_profile_proposals",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.projects.identity_bootstrap.publish_project_event",
            new=AsyncMock(),
            create=True,
        ),
        patch(
            "app.projects.profile_proposals.publish_project_event",
            new=AsyncMock(),
        ),
        patch(
            "app.projects.profile.publish_project_event",
            new=AsyncMock(),
        ),
    ):
        result = asyncio.run(
            bootstrap_identity_from_document(
                session,
                project=project,
                source_document_id=source_id,
                document_text=text,
            )
        )

    assert result.status == "auto_applied"
    assert "site_address" in result.auto_applied_fields
    assert read_profile(project).site_address == (
        "42 Hargrave Street, Paddington NSW 2021"
    )


def test_document_identity_populates_client_and_address_without_confirmation() -> None:
    project = _project()
    source_id = uuid.uuid4()
    session = AsyncMock()
    session.add = MagicMock()
    _flush_assigns_ids(session)

    text = (
        "**Project:** Walsh House — 42 Hargrave Street Paddington NSW 2021\n"
        "Client: Atelier North for David & Emma Walsh\n"
    )

    with (
        patch(
            "app.projects.identity_bootstrap.list_profile_proposals",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.projects.profile_proposals.publish_project_event",
            new=AsyncMock(),
        ),
        patch(
            "app.projects.profile.publish_project_event",
            new=AsyncMock(),
        ),
    ):
        result = asyncio.run(
            bootstrap_identity_from_document(
                session,
                project=project,
                source_document_id=source_id,
                document_text=text,
            )
        )

    assert result.status == "auto_applied"
    assert "site_address" in result.auto_applied_fields
    assert "client" in result.auto_applied_fields
    assert result.proposed_fields == ()
    assert read_profile(project).site_address is not None
    assert read_profile(project).client == "Atelier North for David & Emma Walsh"
    assert result.proposal is not None
    assert result.proposal.state == "accepted"


def test_set_fields_are_not_overwritten() -> None:
    project = _project(
        project_metadata={
            "taxonomy": {
                "subclasses": ["house"],
                "site_address": "1 Existing Street, Sydney NSW 2000",
                "client": "Existing Client",
            }
        }
    )
    session = AsyncMock()
    with patch(
        "app.projects.identity_bootstrap.list_profile_proposals",
        new=AsyncMock(return_value=[]),
    ):
        result = asyncio.run(
            bootstrap_identity_from_document(
                session,
                project=project,
                source_document_id=uuid.uuid4(),
                document_text=(
                    "proposed new dwelling at 14 Wattle Grove, Lindfield NSW 2070\n"
                    "**To:** Someone Else\n"
                ),
            )
        )

    assert result.status == "noop"
    profile = read_profile(project)
    assert profile.site_address == "1 Existing Street, Sydney NSW 2000"
    assert profile.client == "Existing Client"


def test_duplicate_pending_proposal_is_skipped() -> None:
    project = _project()
    pending = ProjectProfileProposal(
        id=uuid.uuid4(),
        project_id=project.id,
        profile_revision=1,
        current_values={},
        proposed_values={"site_address": "42 Hargrave Street, Paddington NSW 2021"},
        evidence_references=[],
        confidence=0.9,
        state="pending",
        proposer="ingest",
        resolver_source=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        resolved_at=None,
    )
    session = AsyncMock()
    from app.schemas.profile_proposals import ProjectProfileProposalView

    with patch(
        "app.projects.identity_bootstrap.list_profile_proposals",
        new=AsyncMock(
            return_value=[ProjectProfileProposalView.model_validate(pending)]
        ),
    ):
        result = asyncio.run(
            bootstrap_identity_from_document(
                session,
                project=project,
                source_document_id=uuid.uuid4(),
                document_text=(
                    "proposed new dwelling at "
                    "42 Hargrave Street, Paddington NSW 2021"
                ),
            )
        )

    assert result.status == "noop"
    session.add.assert_not_called()
