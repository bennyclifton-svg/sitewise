from types import SimpleNamespace
import uuid

from app.sitewise.rfp_renderer import (
    BACKGROUND_PLACEHOLDER,
    INFORMATION_TO_REVIEW_PLACEHOLDER,
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
    assert scaffold.count(INFORMATION_TO_REVIEW_PLACEHOLDER) == 1
    assert "## Project Summary" in scaffold
    assert "| Field | Current PMP position | Citation |" in scaffold
    assert citation_index.documents == (
        ("04-projects/walsh/00-brief/project-brief.pdf", "on file"),
        ("04-projects/walsh/03-design/drawings.pdf", "on file"),
    )
    assert "## Citation key" in scaffold
    assert scaffold.index("[1] project-brief.pdf — on file") < scaffold.index(
        "[2] drawings.pdf — on file"
    )
