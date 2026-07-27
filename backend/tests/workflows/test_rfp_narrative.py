from types import SimpleNamespace

from app.sitewise.rfp_renderer import build_rfp_citation_index
from app.workflows.consultant_procurement import normalise_discipline
from app.workflows.rfp_narrative import build_rfp_narrative_prompt


def test_rfp_narrative_prompt_pairs_each_evidence_snippet_with_its_token() -> None:
    evidence = [
        {
            "relative_path": "04-projects/walsh/03-design/site-plan.pdf",
            "filename": "site-plan.pdf",
            "snippet": "The proposed work retains the existing northern wall.",
        },
        {
            "relative_path": "04-projects/walsh/00-brief/project-brief.pdf",
            "filename": "project-brief.pdf",
            "snippet": "The owners propose a two-storey rear addition.",
        },
    ]
    citation_index = build_rfp_citation_index(evidence)

    prompt = build_rfp_narrative_prompt(
        project=SimpleNamespace(title="Walsh Renovation"),
        target=normalise_discipline("town planner"),
        project_evidence=evidence,
        platform_knowledge=[
            {
                "title": "Procurement guide",
                "snippet": "Request staged fees and explicit exclusions.",
            }
        ],
        citation_index=citation_index,
    )

    for item in evidence:
        token = citation_index.token_for(item["relative_path"])
        assert f"{token} {item['filename']}: {item['snippet']}" in prompt
    assert "Platform knowledge (guidance only, not project evidence):" in prompt


def test_rfp_narrative_prompt_prioritises_project_specific_requested_services() -> None:
    project = SimpleNamespace(
        title="Industrial",
        state="NSW",
        building_class="industrial",
        work_type="extend",
        project_metadata={
            "taxonomy": {
                "subclasses": ["warehouse"],
                "scale": {"gfa_sqm": 2135, "office_percent": 9.3},
            }
        },
    )
    target = normalise_discipline("mechanical engineer")
    evidence = [
        {
            "relative_path": "docs/design-brief.pdf",
            "filename": "design-brief.pdf",
            "snippet": (
                "Warehouse mechanical services include MHE charging ventilation "
                "and smoke clearance."
            ),
        }
    ]
    citation_index = build_rfp_citation_index(evidence)

    prompt = build_rfp_narrative_prompt(
        project=project,
        target=target,
        project_evidence=evidence,
        platform_knowledge=[],
        citation_index=citation_index,
    )

    assert "Project profile:" in prompt
    assert "industrial / extend / warehouse / 2135 m² GFA" in prompt
    assert "Relevant taxonomy emphasis:" in prompt
    assert "scope-client-requirements=" in prompt
    assert "Requested services is the highest-priority RFP section" in prompt
    assert "Baseline requested services to tailor" in prompt
    assert target.requested_services[0] in prompt
    assert "Programme narrative slots" in prompt
