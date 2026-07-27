from types import SimpleNamespace
import uuid

from app.sitewise.rfp_renderer import (
    BACKGROUND_PLACEHOLDER,
    INFORMATION_TO_REVIEW_PLACEHOLDER,
    REQUESTED_SERVICES_PLACEHOLDER,
    build_rfp_citation_index,
    render_rfp_scaffold,
)
from app.workflows.consultant_procurement import normalise_discipline


def _project() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        title="Walsh Renovation",
        state="NSW",
        phase="procurement",
        building_class="residential",
        work_type="refurb",
        user_role="architect-pm",
        profile_revision=1,
        project_metadata={},
    )


def test_rfp_scaffold_has_narrative_markers_and_a_stable_citation_key() -> None:
    evidence = [
        {
            "relative_path": "04-projects/walsh/03-design/drawings.pdf",
            "filename": "drawings.pdf",
        },
        {
            "relative_path": "04-projects/walsh/00-brief/project-brief.pdf",
            "filename": "project-brief.pdf",
        },
        {
            "relative_path": "04-projects/walsh/03-design/drawings.pdf",
            "filename": "drawings.pdf",
        },
    ]
    citation_index = build_rfp_citation_index(evidence)

    scaffold = render_rfp_scaffold(
        project=_project(),
        target=normalise_discipline("town planner"),
        citation_index=citation_index,
        forecast={"used": False},
        max_pages=1,
    )

    assert scaffold.count(BACKGROUND_PLACEHOLDER) == 1
    assert scaffold.count(REQUESTED_SERVICES_PLACEHOLDER) == 1
    assert scaffold.count(INFORMATION_TO_REVIEW_PLACEHOLDER) == 1
    assert "## Project Summary" in scaffold
    assert "| Field | Project detail | Source |" in scaffold
    assert citation_index.documents == (
        ("04-projects/walsh/00-brief/project-brief.pdf", "on file"),
        ("04-projects/walsh/03-design/drawings.pdf", "on file"),
    )
    assert "## Citation key" in scaffold
    assert scaffold.index("[1] project-brief.pdf — on file") < scaffold.index(
        "[2] drawings.pdf — on file"
    )


def test_rfp_summary_cites_evidence_that_corroborates_profile_identity() -> None:
    project = _project()
    project.project_metadata = {
        "taxonomy": {
            "site_address": "145-151 Arthur Street, Homebush West NSW 2140",
            "client": "Hale c/o Engine Room VM",
        }
    }
    evidence = [
        {
            "relative_path": "04-projects/industrial/00-brief/design-brief.pdf",
            "filename": "design-brief.pdf",
            "snippet": (
                "Proposed extension works at 145-151 Arthur Street, "
                "Homebush West NSW for Hale Capital Partners."
            ),
        },
        {
            "relative_path": "04-projects/industrial/03-design/mechanical-sketch.pdf",
            "filename": "mechanical-sketch.pdf",
            "snippet": "Client: Engine Room VM. Warehouse and offices mechanical spatial.",
        },
    ]
    citation_index = build_rfp_citation_index(evidence)

    scaffold = render_rfp_scaffold(
        project=project,
        target=normalise_discipline("mechanical engineer"),
        citation_index=citation_index,
        forecast={"used": False},
        max_pages=1,
        project_evidence=evidence,
    )

    assert (
        "| Site / address | 145-151 Arthur Street, Homebush West NSW 2140 | [1] |"
    ) in scaffold
    assert (
        "| Client | Hale c/o Engine Room VM | [2] |"
    ) in scaffold


def test_rfp_summary_keeps_provenance_in_source_column_without_status_prose() -> None:
    scaffold = render_rfp_scaffold(
        project=_project(),
        target=normalise_discipline("hydraulic engineer"),
        citation_index=build_rfp_citation_index([]),
        forecast={"used": False},
        max_pages=3,
        instructions="Use the supplied project context and do not invent details.",
    )

    summary = scaffold.split("## Project Summary", maxsplit=1)[1].split(
        "## Background", maxsplit=1
    )[0]
    assert "| Project | Walsh Renovation | Profile |" in summary
    assert "| Budget | TBC | Confirm |" in summary
    assert "User provided" not in summary
    assert "Evidence on file" not in summary
    assert "Assumption" not in summary
    assert "Current PMP position" not in summary
    assert "Additional instruction:" not in scaffold
    assert "No internal fee benchmark" not in scaffold


def test_rfp_summary_prefers_evidenced_project_name_over_generic_profile_title() -> None:
    project = _project()
    project.title = "Fitout"
    evidence = [
        {
            "relative_path": "04-projects/fitout/00-brief/fee-proposal.md",
            "filename": "fee-proposal.md",
            "snippet": (
                "To: Meridian Legal Group. Project: Meridian Chambers Fit-Out, "
                "Levels 3 and 4. Date: 10 February 2026."
            ),
        }
    ]
    scaffold = render_rfp_scaffold(
        project=project,
        target=normalise_discipline("hydraulic engineer"),
        citation_index=build_rfp_citation_index(evidence),
        forecast={"used": False},
        max_pages=3,
        project_evidence=evidence,
    )

    assert "| Project | Meridian Chambers Fit-Out | [1] |" in scaffold


def test_rfp_summary_humanises_scale_labels_and_singular_counts() -> None:
    project = _project()
    project.building_class = "commercial"
    project.project_metadata = {
        "taxonomy": {
            "subclasses": ["office"],
            "scale": {
                "nla_sqm": 365,
                "storeys": 2,
                "tenancies": 1,
                "floor_plate_sqm": 180,
            },
        }
    }
    scaffold = render_rfp_scaffold(
        project=project,
        target=normalise_discipline("hydraulic engineer"),
        citation_index=build_rfp_citation_index([]),
        forecast={"used": False},
        max_pages=3,
    )

    assert (
        "| Subclass and scale | office; 365 m² NLA; 2 storeys; "
        "1 tenancy; 180 m² floor plate | Profile |"
    ) in scaffold


def test_consultant_rfp_does_not_truncate_deliverables_to_one_page() -> None:
    scaffold = render_rfp_scaffold(
        project=_project(),
        target=normalise_discipline("mechanical engineer"),
        citation_index=build_rfp_citation_index([]),
        forecast={"used": False},
        max_pages=1,
    )

    assert (
        "Fee breakdown by stage with personnel, meetings, site visits, "
        "disbursements, hourly rates, programme, exclusions, optional services, "
        "and required client inputs."
    ) in scaffold
