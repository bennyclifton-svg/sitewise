import uuid
from datetime import UTC, datetime

from app.schemas.document_selections import SelectedWorkspaceFile, TenderQuoteGroup, TenderQuoteSelection
from app.schemas.project_snapshot import (
    ProjectSnapshot,
    ProjectSnapshotDecisions,
    ProjectSnapshotEvidence,
    ProjectSnapshotIdentity,
    SnapshotValue,
)
from app.schemas.projects import ProjectProfileView
from tender.services.project_context_adapter import map_project_context


def test_residential_refurbishment_maps_to_strict_tender_context() -> None:
    prepared = map_project_context(
        snapshot=_snapshot(building_class="residential", work_type="refurb", state="NSW", subclasses=["house"]),
        selection=_selection(),
        overrides={"region": "metro", "spec_level": "mid"},
    )
    assert prepared.ready is True
    assert prepared.context is not None
    assert prepared.context.build_type == "renovation"
    assert prepared.context.state == "NSW"
    assert prepared.context.storeys == 2
    assert prepared.provenance.source_profile_revision == 7
    assert prepared.provenance.source_selection_revision == 3


def test_commercial_and_unsupported_state_block_clearly() -> None:
    prepared = map_project_context(
        snapshot=_snapshot(building_class="commercial", work_type="new", state="SA", subclasses=["office"]),
        selection=_selection(),
        overrides={"region": "metro", "spec_level": "mid"},
    )
    assert prepared.ready is False
    assert prepared.supported is False
    assert any("residential Class 1a" in reason for reason in prepared.unsupported_reasons)
    assert any("State SA" in reason for reason in prepared.unsupported_reasons)


def _snapshot(*, building_class: str, work_type: str, state: str, subclasses: list[str]) -> ProjectSnapshot:
    project_id = uuid.uuid4()
    return ProjectSnapshot(
        generated_at=datetime.now(UTC),
        content_fingerprint="snapshot-fingerprint",
        identity=ProjectSnapshotIdentity(
            project_id=project_id, title="House", slug="house", workspace_path="projects/house",
            phase="procurement", status="active", site_address=SnapshotValue(status="needs_input"), client=SnapshotValue(status="needs_input"),
        ),
        profile=ProjectProfileView(
            project_id=project_id, profile_revision=7, building_class=building_class,
            work_type=work_type, subclasses=subclasses, scale={"storeys": 2, "gfa_sqm": 250}, state=state,
        ),
        decisions=ProjectSnapshotDecisions(set_revision=1, items=[]),
        evidence=ProjectSnapshotEvidence(fingerprint="evidence", active_count=0, fingerprint_complete=True, ingest_failure_count=0, ingest_failures=[]),
        confirmed_inputs={}, open_profile_proposals=[],
    )


def _selection() -> TenderQuoteSelection:
    project_id = uuid.uuid4()
    groups = []
    for position in range(2):
        file_id = uuid.uuid4()
        groups.append(TenderQuoteGroup(
            group_id=uuid.uuid4(), builder_name=f"Builder {position + 1}", position=position,
            files=[SelectedWorkspaceFile(workspace_file_id=file_id, workspace_path=f"quotes/{position}.pdf", filename=f"{position}.pdf", content_hash="a" * 64, storage_bucket="project-files", storage_key=f"p/{position}.pdf", position=0)],
        ))
    return TenderQuoteSelection(
        selection_id=uuid.uuid4(), selection_revision_id=uuid.uuid4(), project_id=project_id,
        revision=3, selected_by=uuid.uuid4(), created_at=datetime.now(UTC), quote_groups=groups,
    )
