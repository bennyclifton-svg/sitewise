from types import SimpleNamespace

from app.config import settings
from app.sitewise.mobilisation_evidence import MobilisationEvidencePack
from app.sitewise.pmp_evidence_validation import apply_corpus_evidence_downgrades
from app.sitewise.pmp_length import pmp_word_count
from app.sitewise.pmp_renderer import render_pmp_scaffold
from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context
from app.workflows.create_pmp import markdown_section_headings
from app.sitewise.pmp_sources import required_section_headings


def _minimal_brief_project():
    return SimpleNamespace(
        slug="minimal-house",
        title="Residential / new / house / budget $1M",
        workspace_path="04-projects/minimal-house",
        phase="brief-planning",
        archetype=None,
        building_class="residential",
        work_type="new",
        user_role="architect-pm",
        state="NSW",
        project_metadata={
            "taxonomy": {
                "subclasses": ["house"],
                "scale": {"gfa_sqm": 260},
                "budget": "$1,000,000",
            }
        },
    )


def test_minimal_brief_scaffold_meets_phase6_contract() -> None:
    project = _minimal_brief_project()
    context = pmp_taxonomy_context(project)
    assert context is not None

    markdown = render_pmp_scaffold(
        project,
        MobilisationEvidencePack(),
        "platform_seeded",
    )

    assert markdown_section_headings(markdown) == list(
        required_section_headings(project.user_role, project=project)
    )
    assert settings.pmp_min_words <= pmp_word_count(markdown) <= settings.pmp_max_words * 1.05
    assert "Grounded" not in markdown
    assert "User provided" in markdown
    assert "$1,000,000" in markdown or "$1M" in markdown
    assert markdown.count("```pmp-decision") >= 4
    assert "Annexure" in markdown or "annexure" in markdown.lower()


def test_empty_corpus_refresh_downgrades_formerly_grounded_rows() -> None:
    markdown = (
        "## Evidence basis and document control\n\n"
        "| Section | Evidence status | Ref |\n"
        "| --- | --- | --- |\n"
        "| Appointment & fee | Grounded | engagement letter |\n"
        "| Budget | User provided | owner brief |\n"
    )
    updated, meta = apply_corpus_evidence_downgrades(
        markdown,
        removed_paths={"04-projects/minimal-house/01-engagement-letter.md"},
        current_source_texts=[],
    )
    assert "Not evidenced" in updated
    assert "User provided" in updated
    assert "current corpus no longer supports" in updated
    assert meta["downgraded"]
    assert meta["conflicted"]
