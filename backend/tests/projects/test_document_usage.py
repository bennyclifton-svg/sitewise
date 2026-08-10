from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.projects.document_usage import (
    latest_document_usage,
    relative_path_from_source_ref,
    usage_marks_by_relative_path,
)
from tests.conftest import run_async

PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _draft(
    *,
    workflow_type: str = "create_pmp",
    version: int = 1,
    title: str = "Project Management Plan",
    evidence_refs: list[str] | None = None,
    issued_document_refs: list[str] | None = None,
    artefact_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=artefact_id or uuid.uuid4(),
        workflow_type=workflow_type,
        version=version,
        title=title,
        provenance_metadata={
            "evidence_refs": evidence_refs or [],
            "issued_document_refs": issued_document_refs or [],
        },
    )


class TestRelativePathFromSourceRef:
    def test_extracts_path_from_a_full_source_ref(self):
        ref = "project_evidence:04-projects/chen/01-brief/owner-brief.pdf#chunk=abc"

        assert (
            relative_path_from_source_ref(ref)
            == "04-projects/chen/01-brief/owner-brief.pdf"
        )

    def test_extracts_path_when_no_chunk_fragment_is_present(self):
        ref = "project_evidence:04-projects/chen/01-brief/owner-brief.pdf"

        assert (
            relative_path_from_source_ref(ref)
            == "04-projects/chen/01-brief/owner-brief.pdf"
        )

    def test_treats_a_bare_path_as_the_path(self):
        assert relative_path_from_source_ref("04-projects/chen/brief.pdf") == (
            "04-projects/chen/brief.pdf"
        )

    def test_normalises_windows_separators(self):
        ref = "project_evidence:04-projects\\chen\\brief.pdf#chunk=abc"

        assert relative_path_from_source_ref(ref) == "04-projects/chen/brief.pdf"

    def test_returns_none_for_a_ref_with_no_path(self):
        assert relative_path_from_source_ref("project_evidence:#chunk=abc") is None
        assert relative_path_from_source_ref("   ") is None
        assert relative_path_from_source_ref("") is None


class TestUsageMarksByRelativePath:
    def test_marks_each_cited_document(self):
        draft = _draft(
            evidence_refs=[
                "project_evidence:04-projects/chen/brief.pdf#chunk=1",
                "project_evidence:04-projects/chen/survey.pdf#chunk=2",
            ]
        )

        marks = usage_marks_by_relative_path([draft])

        assert set(marks) == {
            "04-projects/chen/brief.pdf",
            "04-projects/chen/survey.pdf",
        }

    def test_collapses_repeated_chunks_of_one_document_into_a_single_mark(self):
        draft = _draft(
            evidence_refs=[
                "project_evidence:04-projects/chen/brief.pdf#chunk=1",
                "project_evidence:04-projects/chen/brief.pdf#chunk=2",
                "project_evidence:04-projects/chen/brief.pdf#chunk=3",
            ]
        )

        marks = usage_marks_by_relative_path([draft])

        assert len(marks["04-projects/chen/brief.pdf"]) == 1

    def test_marks_every_document_issued_with_a_procurement_request(self):
        draft = _draft(
            workflow_type="trade_rft_main_works",
            evidence_refs=[
                "project_evidence:04-projects/mosaic/00-brief-pmp/ppr.pdf#chunk=1"
            ],
            issued_document_refs=[
                "04-projects/mosaic/00-brief-pmp/ppr.pdf",
                "04-projects/mosaic/03-design/architect/A001.pdf",
                "04-projects/mosaic/03-design/electrical/E001.pdf",
            ],
        )

        marks = usage_marks_by_relative_path([draft])

        assert set(marks) == {
            "04-projects/mosaic/00-brief-pmp/ppr.pdf",
            "04-projects/mosaic/03-design/architect/A001.pdf",
            "04-projects/mosaic/03-design/electrical/E001.pdf",
        }
        assert len(marks["04-projects/mosaic/00-brief-pmp/ppr.pdf"]) == 1

    def test_mark_carries_the_artefact_identity(self):
        artefact_id = uuid.uuid4()
        draft = _draft(
            artefact_id=artefact_id,
            workflow_type="create_pmp",
            version=3,
            title="Project Management Plan",
            evidence_refs=["project_evidence:04-projects/chen/brief.pdf#chunk=1"],
        )

        mark = usage_marks_by_relative_path([draft])["04-projects/chen/brief.pdf"][0]

        assert mark.artefact_id == artefact_id
        assert mark.workflow_type == "create_pmp"
        assert mark.version == 3
        assert mark.title == "Project Management Plan"

    def test_one_document_used_by_two_artefacts_gets_two_marks(self):
        pmp = _draft(
            workflow_type="create_pmp",
            evidence_refs=["project_evidence:04-projects/chen/brief.pdf#chunk=1"],
        )
        cost_plan = _draft(
            workflow_type="create_cost_plan",
            title="Cost Plan",
            evidence_refs=["project_evidence:04-projects/chen/brief.pdf#chunk=9"],
        )

        marks = usage_marks_by_relative_path([pmp, cost_plan])

        assert [mark.workflow_type for mark in marks["04-projects/chen/brief.pdf"]] == [
            "create_cost_plan",
            "create_pmp",
        ]

    def test_only_the_latest_version_of_each_workflow_counts(self):
        superseded = _draft(
            version=1,
            evidence_refs=["project_evidence:04-projects/chen/old.pdf#chunk=1"],
        )
        latest = _draft(
            version=2,
            evidence_refs=["project_evidence:04-projects/chen/new.pdf#chunk=1"],
        )

        marks = usage_marks_by_relative_path([superseded, latest])

        assert set(marks) == {"04-projects/chen/new.pdf"}
        assert marks["04-projects/chen/new.pdf"][0].version == 2

    def test_ignores_drafts_with_no_provenance_metadata(self):
        draft = _draft()
        draft.provenance_metadata = None

        assert usage_marks_by_relative_path([draft]) == {}

    def test_ignores_a_non_list_evidence_refs_value(self):
        draft = _draft()
        draft.provenance_metadata = {"evidence_refs": "not-a-list"}

        assert usage_marks_by_relative_path([draft]) == {}

    def test_returns_empty_for_no_drafts(self):
        assert usage_marks_by_relative_path([]) == {}


class TestLatestDocumentUsage:
    def test_maps_project_drafts_to_usage_marks(self):
        draft = _draft(
            evidence_refs=["project_evidence:04-projects/chen/brief.pdf#chunk=1"]
        )
        result = MagicMock()
        result.all.return_value = [draft]
        session = AsyncMock()
        session.execute.return_value = result

        marks = run_async(latest_document_usage(session, project_id=PROJECT_ID))

        assert set(marks) == {"04-projects/chen/brief.pdf"}
