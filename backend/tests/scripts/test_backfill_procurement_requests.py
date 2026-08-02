from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from scripts.backfill_procurement_requests import (
    backfill,
    latest_legacy_lineages,
    legacy_request_details,
)
from tests.conftest import run_async


def _draft(
    *,
    project_id: str = "project-1",
    workflow_type: str,
    version: int = 1,
    metadata: dict | None = None,
):
    return SimpleNamespace(
        id="draft-1",
        project_id=project_id,
        workflow_type=workflow_type,
        version=version,
        provenance_metadata=metadata,
        author_user_id="user-1",
    )


class _Result:
    def __init__(self, *, scalar=None, scalars=()):
        self.scalar = scalar
        self.values = scalars

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return self.values


def test_backfill_groups_latest_version_per_project_workflow_lineage() -> None:
    v1 = _draft(workflow_type="consultant_procurement_structural_engineer", version=1)
    v2 = _draft(workflow_type="consultant_procurement_structural_engineer", version=2)
    eoi = _draft(workflow_type="contractor_eoi_main_works")
    unrelated = _draft(workflow_type="create_pmp")

    assert latest_legacy_lineages([v1, eoi, unrelated, v2]) == [v2, eoi]


def test_backfill_prefers_provenance_target_and_falls_back_to_workflow_suffix() -> None:
    consultant = _draft(
        workflow_type="consultant_procurement_structural_engineer",
        metadata={"discipline": "Structural Engineer"},
    )
    eoi = _draft(workflow_type="contractor_eoi_main_works")

    assert legacy_request_details(consultant) == ("consultant_rfp", "Structural Engineer")
    assert legacy_request_details(eoi) == ("contractor_eoi", "main works")


def test_backfill_creates_once_and_skips_the_same_current_draft_on_rerun() -> None:
    draft = _draft(
        workflow_type="consultant_procurement_structural_engineer",
        metadata={"discipline": "Structural Engineer"},
    )
    request = SimpleNamespace(id="request-1", status="draft")
    first_session = AsyncMock()
    first_session.execute = AsyncMock(
        side_effect=[
            _Result(scalars=[draft]),
            _Result(),
            _Result(scalars=[]),
        ]
    )

    with (
        patch(
            "scripts.backfill_procurement_requests.create_procurement_request",
            new=AsyncMock(return_value=request),
        ) as create,
        patch(
            "scripts.backfill_procurement_requests.attach_current_draft",
            new=AsyncMock(return_value=request),
        ) as attach,
    ):
        report = run_async(backfill(first_session, apply=True))

    assert (report.created, report.attached, report.skipped) == (1, 1, 0)
    create.assert_awaited_once()
    attach.assert_awaited_once_with(first_session, request=request, draft=draft)
    assert draft.provenance_metadata["procurement_request_id"] == "request-1"

    rerun_session = AsyncMock()
    rerun_session.execute = AsyncMock(
        side_effect=[_Result(scalars=[draft]), _Result(scalar=request)]
    )

    rerun_report = run_async(backfill(rerun_session, apply=True))

    assert (rerun_report.created, rerun_report.attached, rerun_report.skipped) == (0, 0, 1)
