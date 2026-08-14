import re
from types import SimpleNamespace
import uuid

from app.sitewise.rfp_renderer import (
    BACKGROUND_PLACEHOLDER,
    PROJECT_PROFILE_CITATION_LABEL,
    REQUESTED_SERVICES_PLACEHOLDER,
    build_rfp_citation_index,
    detect_rfp_identity_conflicts,
    render_rfp_scaffold,
    replace_transmittal_section,
)
from app.workflows.consultant_procurement import normalise_discipline


def test_rfp_citation_index_reserves_project_profile_as_one() -> None:
    evidence = [
        {
            "relative_path": "04-projects/walsh/03-design/drawings.pdf",
            "filename": "drawings.pdf",
        },
        {
            "relative_path": "04-projects/walsh/00-brief/project-brief.pdf",
            "filename": "project-brief.pdf",
        },
    ]
    index = build_rfp_citation_index(evidence)

    assert index.token_for(PROJECT_PROFILE_CITATION_LABEL) == "[1]"
    assert index.token_for("04-projects/walsh/00-brief/project-brief.pdf") == "[2]"
    assert index.token_for("04-projects/walsh/03-design/drawings.pdf") == "[3]"
    assert index.documents[0] == (PROJECT_PROFILE_CITATION_LABEL, "current")


def test_rfp_scaffold_includes_citation_key_with_profile_first() -> None:
    evidence = [
        {
            "relative_path": "04-projects/walsh/00-brief/project-brief.pdf",
            "filename": "project-brief.pdf",
            "document_metadata": {
                "document_number": "001",
                "title": "Project brief",
                "revision": "A",
                "discipline": "Project",
            },
        }
    ]
    scaffold = render_rfp_scaffold(
        project=_project(),
        target=normalise_discipline("certifier"),
        citation_index=build_rfp_citation_index(evidence),
        forecast={"used": False},
        max_pages=1,
        project_evidence=evidence,
    )

    assert "## Citation key" in scaffold
    citation_key = scaffold.split("## Citation key", maxsplit=1)[1].split(
        "## Trace & QA", maxsplit=1
    )[0]
    assert "- [1] Project Profile — current" in citation_key
    assert "- [2] project-brief.pdf — on file" in citation_key
    assert scaffold.index("## Citation key") < scaffold.index("## Trace & QA")


def test_rfp_summary_cites_project_profile_as_one_when_no_corroborating_evidence() -> (
    None
):
    project = _project()
    project.project_metadata = {
        "taxonomy": {
            "site_address": "12 Example Street, Sydney NSW 2000",
            "client": "Example Client Pty Ltd",
        }
    }
    scaffold = render_rfp_scaffold(
        project=project,
        target=normalise_discipline("certifier"),
        citation_index=build_rfp_citation_index([]),
        forecast={"used": False},
        max_pages=1,
    )

    summary = scaffold.split("## Proposal particulars", maxsplit=1)[1].split(
        "## Background", maxsplit=1
    )[0]
    assert "| Project | Walsh Renovation | [1] |" in summary
    assert "| Site / address | 12 Example Street, Sydney NSW 2000 | [1] |" in summary
    assert "| Client | Example Client Pty Ltd | [1] |" in summary
    assert "| State | NSW | [1] |" in summary
    assert "| Taxonomy | residential / refurb | [1] |" in summary
    assert "Profile" not in summary
    assert "Confirm" not in summary


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


def test_rfp_scaffold_has_narrative_markers_and_a_stable_document_register() -> None:
    evidence = [
        {
            "relative_path": "04-projects/walsh/03-design/drawings.pdf",
            "filename": "drawings.pdf",
            "document_metadata": {
                "document_number": "420",
                "title": "Structural details",
                "revision": "P3",
                "discipline": "Structural",
            },
        },
        {
            "relative_path": "04-projects/walsh/00-brief/project-brief.pdf",
            "filename": "project-brief.pdf",
            "document_metadata": {
                "document_number": "001",
                "title": "Project brief",
                "revision": "A",
                "discipline": "Project",
            },
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
        project_evidence=evidence,
    )

    assert scaffold.count(BACKGROUND_PLACEHOLDER) == 1
    assert scaffold.count(REQUESTED_SERVICES_PLACEHOLDER) == 1
    assert scaffold.startswith("# Request for Proposal - Town planner")
    assert "## Proposal particulars" in scaffold
    assert "| Field | Project detail | Source |" not in scaffold
    assert "| Project |" in scaffold
    assert "| --- | --- | --- |" in scaffold
    assert citation_index.documents == (
        (PROJECT_PROFILE_CITATION_LABEL, "current"),
        ("04-projects/walsh/00-brief/project-brief.pdf", "on file"),
        ("04-projects/walsh/03-design/drawings.pdf", "on file"),
    )
    assert "| Document number | Title | Rev | Category |" in scaffold
    assert "| 001 | Project brief | A | Project |" in scaffold
    assert "| 420 | Structural details | P3 | Structural |" in scaffold
    assert "## Citation key" in scaffold
    assert "- [1] Project Profile — current" in scaffold
    assert len(re.findall(r"^## ", scaffold, flags=re.MULTILINE)) == 9
    assert "Provide a concise return brief" in scaffold
    assert (
        "| Indicative fee stage | Scope / allowance to identify | Fee ex GST |"
        in scaffold
    )
    assert "## Scope assumptions / exclusions to state" not in scaffold
    assert "## Site visit / clarifications" not in scaffold
    assert "## Submission instructions" not in scaffold
    assert scaffold.rstrip().endswith("- No unresolved generation inputs recorded.")
    assert "TBC" not in scaffold.split("## Trace & QA", maxsplit=1)[0]


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
        "| Site / address | 145-151 Arthur Street, Homebush West NSW 2140 | [2] |"
    ) in scaffold
    assert ("| Client | Hale c/o Engine Room VM | [3] |") in scaffold


def test_rfp_summary_keeps_provenance_in_source_column_without_status_prose() -> None:
    scaffold = render_rfp_scaffold(
        project=_project(),
        target=normalise_discipline("hydraulic engineer"),
        citation_index=build_rfp_citation_index([]),
        forecast={"used": False},
        max_pages=3,
        instructions="Use the supplied project context and do not invent details.",
    )

    summary = scaffold.split("## Proposal particulars", maxsplit=1)[1].split(
        "## Background", maxsplit=1
    )[0]
    assert "| Project | Walsh Renovation | [1] |" in summary
    assert "Profile" not in summary
    assert "Confirm" not in summary
    assert "| Budget |" not in summary
    assert "User provided" not in summary
    assert "Evidence on file" not in summary
    assert "Assumption" not in summary
    assert "Current PMP position" not in summary
    assert "Additional instruction:" not in scaffold
    assert "No internal fee benchmark" not in scaffold


def test_rfp_summary_uses_current_cost_plan_construction_budget() -> None:
    scaffold = render_rfp_scaffold(
        project=_project(),
        target=normalise_discipline("structural engineer"),
        citation_index=build_rfp_citation_index([]),
        forecast={
            "used": False,
            "construction_budget": 400_000,
            "construction_budget_basis": "user_adopted",
            "source_path": "04-projects/greenbank/01-cost/cost_plan_v03.md",
        },
        max_pages=3,
    )

    assert "| Budget | $400,000 ex GST |  |" in scaffold


def test_rfp_summary_prefers_evidenced_project_name_over_generic_profile_title() -> (
    None
):
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

    assert "| Project | Meridian Chambers Fit-Out | [2] |" in scaffold


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
        "| Subclass and scale | Office (Class 5); 365 m² NLA; 2 storeys; "
        "1 tenancy; 180 m² floor plate | [1] |"
    ) in scaffold


def test_rfp_summary_singularises_one_garage_space() -> None:
    project = _project()
    project.project_metadata = {
        "taxonomy": {
            "subclasses": ["house"],
            "scale": {"bedrooms": 4, "garage_spaces": 1},
        }
    }

    scaffold = render_rfp_scaffold(
        project=project,
        target=normalise_discipline("structural engineer"),
        citation_index=build_rfp_citation_index([]),
        forecast={"used": False},
        max_pages=3,
    )

    assert "4 bedrooms; 1 garage space" in scaffold


def test_detect_rfp_identity_conflicts_flags_address_mismatch() -> None:
    project = _project()
    project.project_metadata = {
        "taxonomy": {"site_address": "82 Queen Street, Petersham NSW 2049"}
    }
    evidence = [
        {
            "relative_path": "04-projects/petersham/_inbox/pbdb.pdf",
            "filename": "pbdb.pdf",
            "snippet": (
                "Address: 568-572 Parramatta Rd, Petersham, NSW. "
                "Project Reference Number 22372-PS2."
            ),
        }
    ]

    notes = detect_rfp_identity_conflicts(project=project, project_evidence=evidence)

    assert len(notes) == 1
    assert "82 Queen Street" in notes[0]
    assert "pbdb.pdf" in notes[0]


def test_rfp_scaffold_surfaces_identity_conflict_in_trace_qa() -> None:
    from app.workflows.consultant_procurement import _assumptions_and_missing_inputs

    project = _project()
    project.project_metadata = {
        "taxonomy": {
            "site_address": "82 Queen Street, Petersham NSW 2049",
            "client": "JOINS WIN PTY LTD",
        }
    }
    evidence = [
        {
            "role": "project_brief",
            "relative_path": "04-projects/petersham/_inbox/pbdb.pdf",
            "filename": "pbdb.pdf",
            "snippet": "Address: 568-572 Parramatta Rd, Petersham, NSW.",
        }
    ]
    assumptions, missing = _assumptions_and_missing_inputs(
        project=project,
        evidence=evidence,
        forecast={"used": False},
        profile=normalise_discipline("certifier"),
    )
    scaffold = render_rfp_scaffold(
        project=project,
        target=normalise_discipline("certifier"),
        citation_index=build_rfp_citation_index(evidence),
        forecast={"used": False},
        max_pages=1,
        project_evidence=evidence,
        assumptions=assumptions,
        missing_inputs=missing,
    )

    qa = scaffold.split("## Trace & QA", maxsplit=1)[1]
    assert "Site address conflict" in qa
    assert "82 Queen Street" in qa
    assert "Resolve profile versus evidence identity conflicts" in qa


def test_certifier_evidence_queries_prioritise_approvals() -> None:
    from app.workflows.consultant_procurement import _evidence_queries

    queries = _evidence_queries(normalise_discipline("certifier"))
    assert queries[0].key == "planning_pathway"
    assert "construction certificate" in queries[0].query.casefold()
    assert any(query.key == "discipline_requirements" for query in queries)
    assert not any(query.key == "project_scope" for query in queries)


def test_certifier_rfp_uses_pca_fee_stages_and_numbered_deliverables() -> None:
    scaffold = render_rfp_scaffold(
        project=_project(),
        target=normalise_discipline("certifier"),
        citation_index=build_rfp_citation_index([]),
        forecast={"used": False},
        max_pages=3,
    )

    assert "Concept design" not in scaffold
    assert "Detailed design and documentation" not in scaffold
    assert "| Construction approval support" in scaffold
    assert "| Critical-stage inspection regime" in scaffold
    assert "| Occupation certificate / completion" in scaffold
    assert "1. Certification fee proposal with statutory role" in scaffold
    assert "- Certification fee proposal with statutory role" not in scaffold


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


def test_consultant_rft_keeps_citations_prominent_and_qa_out_of_issue_body() -> None:
    evidence = [
        {
            "relative_path": "04-projects/walsh/00-brief/project-brief.pdf",
            "filename": "project-brief.pdf",
            "document_metadata": {"title": "Project brief", "revision": "A"},
        }
    ]
    scaffold = render_rfp_scaffold(
        project=_project(),
        target=normalise_discipline("mechanical engineer"),
        citation_index=build_rfp_citation_index(evidence),
        forecast={"used": False},
        max_pages=3,
        project_evidence=evidence,
        missing_inputs=["Tender close date"],
    )

    primary, qa = scaffold.split("## Trace & QA", maxsplit=1)
    assert primary.index("## Proposal conditions and RFI process") < primary.index(
        "## Transmittal"
    )
    assert scaffold.index("## Transmittal") < scaffold.index("## Trace & QA")
    assert "Tender close date" not in primary
    assert "Tender close date" in qa
    assert "TBC" not in primary


def test_information_register_is_distinct_from_cited_narrative_evidence() -> None:
    cited = [
        {
            "relative_path": "04-projects/walsh/00-brief-pmp/ppr.pdf",
            "filename": "ppr.pdf",
            "document_metadata": {"title": "Principal's Project Requirements"},
        }
    ]
    issued = [
        *cited,
        {
            "relative_path": "04-projects/walsh/03-design/electrical/E001.pdf",
            "filename": "E001.pdf",
            "document_metadata": {
                "document_number": "E001",
                "title": "Electrical layout",
                "revision": "C",
                "discipline": "Electrical",
            },
        },
    ]
    scaffold = render_rfp_scaffold(
        project=_project(),
        target=normalise_discipline("electrical engineer"),
        citation_index=build_rfp_citation_index(cited),
        forecast={"used": False},
        max_pages=3,
        project_evidence=cited,
        issued_documents=issued,
    )

    assert "## Transmittal (2 documents)" in scaffold
    assert "| Document number | Title | Rev | Category |" in scaffold
    assert "| E001 | Electrical layout | C | Electrical |" in scaffold
    assert "| Citation |" not in scaffold


def test_replace_transmittal_section_rewrites_legacy_project_documents() -> None:
    markdown = "\n".join(
        [
            "# Request for Proposal",
            "",
            "## Project Documents (1 document)",
            "",
            "| Document number | Title | Rev | Category |",
            "| --- | --- | --- | --- |",
            "| A001 | Old drawing | A | Architectural |",
            "",
            "## Citation key",
            "[1] Project Profile — current",
            "",
        ]
    )
    updated = replace_transmittal_section(
        markdown,
        [
            {
                "relative_path": "04-projects/demo/E001.pdf",
                "filename": "E001.pdf",
                "document_metadata": {
                    "document_number": "E001",
                    "title": "Electrical layout",
                    "revision": "C",
                    "discipline": "Electrical",
                },
            }
        ],
    )

    assert "## Transmittal (1 document)" in updated
    assert "## Project Documents" not in updated
    assert "| E001 | Electrical layout | C | Electrical |" in updated
    assert "| A001 | Old drawing | A | Architectural |" not in updated
    assert updated.index("## Transmittal") < updated.index("## Citation key")
