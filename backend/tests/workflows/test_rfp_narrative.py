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
