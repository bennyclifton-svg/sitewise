from types import SimpleNamespace

import pytest

from app.config import settings
from app.sitewise.mobilisation_evidence import MobilisationEvidencePack
from app.sitewise.pmp_greenfield_brief import build_greenfield_brief
from app.sitewise.pmp_length import length_violations, pmp_word_count
from app.sitewise.pmp_renderer import render_pmp_scaffold
from app.sitewise.pmp_sources import required_section_headings
from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context
from app.sitewise.section_contracts import heading_for_section_id
from app.sitewise.taxonomy import scale_band_word_bounds
from app.workflows.create_pmp import markdown_section_headings


FIRE_REFS = {
    "compliance-approvals": (
        "seed/as-standards-reference.md#as-2419-series-fire-hydrant-installations",
        "seed/as-standards-reference.md#as-2941-fixed-fire-protection-installations-pumpset-systems",
    )
}


def _project(
    *,
    title: str = "Benny Fire Upgrade",
    building_class: str = "commercial",
    work_type: str = "refurb",
    subclasses: list[str] | None = None,
    scale: dict | None = None,
    complexity: dict | None = None,
    work_scope: list[str] | None = None,
):
    return SimpleNamespace(
        slug=title.lower().replace(" ", "-"),
        title=title,
        workspace_path=f"04-projects/{title.lower().replace(' ', '-')}",
        phase="brief-planning",
        archetype=None,
        building_class=building_class,
        work_type=work_type,
        state="NSW",
        project_metadata={
            "taxonomy": {
                "subclasses": ["office"] if subclasses is None else subclasses,
                "scale": {"nla_sqm": 1200, "storeys": 3} if scale is None else scale,
                "complexity": (
                    {"operational_constraints": "live_environment"}
                    if complexity is None
                    else complexity
                ),
                "work_scope": ["fire_services"] if work_scope is None else work_scope,
                "budget": "$1,000,000",
            }
        },
    )



def _word_bounds(project) -> tuple[int, int]:
    """Length bounds scale with the project's band and its applicable sections."""
    context = pmp_taxonomy_context(project)
    return scale_band_word_bounds(
        getattr(context, "scale_band", None),
        section_count=len(getattr(context, "sections", ()) or ()) or None,
        default_min=settings.pmp_min_words,
        default_max=settings.pmp_max_words,
    )


def _min_words(project) -> int:
    return _word_bounds(project)[0]


def _max_words(project) -> int:
    return _word_bounds(project)[1]

def test_adaptive_greenfield_contract_has_budgets_and_fire_as_refs() -> None:
    project = _project()
    context = pmp_taxonomy_context(project)
    assert context is not None
    target_words = (settings.pmp_min_words + settings.pmp_max_words) // 2

    brief = build_greenfield_brief(
        archetype="",
        state="NSW",
        draft_mode="platform_seeded",
        building_class=context.building_class,
        work_type=context.work_type,
        subclasses=context.subclasses,
        scale=context.scale,
        complexity=context.complexity,
        work_scope=context.work_scope,
        risk_flags=context.risk_flags,
        section_weights=context.section_weights,
        seed_section_refs=FIRE_REFS,
        user_provided_fields=context.user_provided_fields,
        target_words=target_words,
    )

    assert "Planning and Compliance (~" in brief
    assert "AS 2419.1 hydrant systems" in brief
    assert "AS 2941 pumpsets" in brief
    assert FIRE_REFS["compliance-approvals"][0] in brief
    assert "Fire Services" in brief

    brief_line = next(
        line for line in brief.splitlines() if line.startswith("- Brief (~")
    )
    assert "finishes" in brief_line.lower() or "physical" in brief_line.lower()
    assert "expected consultant" not in brief_line.lower()
    assert "Fire Engineer" not in brief_line

    consultants_line = next(
        line for line in brief.splitlines() if line.startswith("- Consultants (~")
    )
    assert "appointment" in consultants_line.lower() or "Architect" in consultants_line
    assert "Fire Engineer" in consultants_line

    roster_header = "### Consultants roster (appointment register — not Brief)"
    assert roster_header in brief
    roster_body = brief.split(roster_header, 1)[1].split("### ", 1)[0]
    assert "Fire Engineer" in roster_body

    citation_line = next(
        line for line in brief.splitlines() if line.startswith("- Citation key (~")
    )
    citation_lower = citation_line.lower()
    assert (
        "numbered" in citation_lower
        or "section status" in citation_lower
        or "document control" in citation_lower
    )

    budgets = []
    for line in brief.splitlines():
        if "(~" not in line or " words)" not in line:
            continue
        budgets.append(int(line.split("(~", 1)[1].split(" words)", 1)[0]))
    assert abs(sum(budgets) - target_words) <= len(budgets)


def test_evidence_grounded_contract_omits_empty_fallback_work_scope_prompt() -> None:
    project = _project(work_scope=[])
    context = pmp_taxonomy_context(project)
    assert context is not None

    brief = build_greenfield_brief(
        archetype="",
        state="NSW",
        draft_mode="evidence_grounded",
        building_class=context.building_class,
        work_type=context.work_type,
        subclasses=context.subclasses,
        scale=context.scale,
        complexity=context.complexity,
        work_scope=context.work_scope,
        risk_flags=context.risk_flags,
        section_weights=context.section_weights,
        seed_section_refs={},
        user_provided_fields=context.user_provided_fields,
        target_words=(settings.pmp_min_words + settings.pmp_max_words) // 2,
    )

    assert "No work-scope items selected" not in brief
    assert "confirm physical brief inclusions" not in brief
    assert "### Selected work-scope items" not in brief


def test_taxonomy_platform_seeded_scaffold_has_universal_sections_and_provenance() -> None:
    project = _project()
    markdown = render_pmp_scaffold(
        project,
        MobilisationEvidencePack(),
        "platform_seeded",
        seed_section_refs=FIRE_REFS,
    )
    headings = markdown_section_headings(markdown)

    assert headings == list(required_section_headings(project=project))
    assert headings[-1] == "Citation key"
    assert "| Field | Project detail | Citation |" not in markdown
    summary = _section_body(markdown, "Project Summary")
    assert "| Project | Benny Fire Upgrade |  |" in summary
    assert "| Owner |" in summary
    assert "| Address |" in summary
    assert "| Description |" in summary
    assert "Critical current position" not in summary
    assert "| Expected consultants |" not in markdown
    # Fire services with no fitout scope and no asset register: nothing is being
    # finished or furnished, so the schedule is not applicable to this project.
    assert "## FFE Schedule" not in markdown
    assert "## Consultants" in markdown
    assert "Fire Engineer" in _section_body(markdown, "Consultants")
    assert "| Expected consultants |" not in _section_body(markdown, "Brief")
    assert headings.index("Brief") + 1 == headings.index("Consultants")
    assert _min_words(project) <= pmp_word_count(markdown) <= _max_words(project) * 1.05
    assert "User provided" not in markdown
    assert "Assumption" in markdown
    assert "Not evidenced" in markdown
    assert "Grounded" not in markdown
    assert markdown.count("```pmp-decision") >= 4
    assert length_violations(
        markdown,
        weights=pmp_taxonomy_context(project).section_weights,
        min_words=_min_words(project),
        max_words=_max_words(project),
    ) == []


def test_taxonomy_consultants_cites_natural_engagement_filename() -> None:
    """Non-slug engagement filenames must still resolve to shared [n] citations."""
    engagement_ref = "02-evidence/Letter of Engagement.pdf"
    pack = MobilisationEvidencePack(
        engagement_executed_date="2026-03-01",
        appointee="Studio Example",
        roles="Architect",
        scope_bullets=["PMP", "governance", "procurement advice"],
        fee_total_ex_gst="$12,000",
        evidence_refs=[engagement_ref, "02-evidence/site-survey.pdf"],
    )
    markdown = render_pmp_scaffold(
        _project(),
        pack,
        "platform_seeded",
        version=3,
        seed_section_refs=FIRE_REFS,
    )
    consultants = _section_body(markdown, "Consultants")
    citation_key = _section_body(markdown, "Citation key")

    # The engagement citation attaches to whichever discipline leads design —
    # on a fire-services refurb that is the Fire Engineer, not the Architect.
    lead_row = next(
        line for line in consultants.splitlines() if line.startswith("| Fire Engineer |")
    )
    assert lead_row.rstrip().endswith("| [1] |")
    assert "- [1] Letter of Engagement.pdf — on file" in citation_key
    assert "draft v03" in citation_key
    assert "| Section | Evidence status | Citation |" not in citation_key
    assert "| Consultants | Partial | [1] |" not in citation_key


def test_commercial_fire_scaffold_is_compliance_heavy_and_not_residential() -> None:
    project = _project()
    markdown = render_pmp_scaffold(
        project,
        MobilisationEvidencePack(),
        "platform_seeded",
        seed_section_refs=FIRE_REFS,
    )
    counts = dict(_section_word_counts(markdown))

    assert counts["Planning and Compliance"] > counts["Brief"]
    assert counts["Planning and Compliance"] > counts["Risks and mitigations"]
    assert "AS 2419.1" in markdown
    assert "AS 2941" in markdown
    assert "Fire Engineer" in _section_body(markdown, "Consultants")
    assert "| Expected consultants |" not in _section_body(markdown, "Brief")
    assert "BASIX" not in markdown
    assert "HBCF" not in markdown
    assert _risk_table_row_count(markdown) <= 8
    assert "Critical Infrastructure" in markdown
    assert "Live Operational Environment" in markdown


def test_residential_new_scaffold_is_scope_heavy_and_covers_finishes() -> None:
    project = _project(
        title="Residential New House",
        building_class="residential",
        work_type="new",
        subclasses=["house"],
        scale={"gfa_sqm": 240, "storeys": 2},
        complexity={},
        work_scope=["substructure", "superstructure", "waterproofing"],
    )
    markdown = render_pmp_scaffold(project, MobilisationEvidencePack(), "platform_seeded")
    counts = dict(_section_word_counts(markdown))

    assert counts["Brief"] > counts["Planning and Compliance"]
    assert counts["Brief"] > counts["Risks and mitigations"]
    assert "finishes" in markdown.lower()
    assert "fixtures" in markdown.lower()
    assert "owner selections" in markdown.lower()
    assert markdown_section_headings(markdown)[-1] == "Citation key"


@pytest.mark.parametrize(
    "project,seed_refs",
    [
        (
            _project(
                title="Residential Base Case",
                building_class="residential",
                work_type="new",
                subclasses=["house"],
                scale={"gfa_sqm": 220, "storeys": 2},
                complexity={},
                work_scope=["substructure", "superstructure"],
            ),
            {},
        ),
        (
            _project(
                title="Residential Refurb",
                building_class="residential",
                work_type="refurb",
                subclasses=["house"],
                scale={"gfa_sqm": 180},
                complexity={"operational_constraints": "partial_occupation"},
                work_scope=["building_condition", "stripout"],
            ),
            {},
        ),
        (
            _project(
                title="Commercial New Office",
                building_class="commercial",
                work_type="new",
                subclasses=["office"],
                scale={"nla_sqm": 4000, "storeys": 6},
                complexity={"operational_constraints": "live_environment"},
                work_scope=["mechanical_hvac", "electrical_power"],
            ),
            {},
        ),
        (
            _project(
                title="Industrial Warehouse",
                building_class="industrial",
                work_type="new",
                subclasses=["warehouse"],
                scale={"gfa_sqm": 10000, "clear_height_m": 12},
                complexity={},
                work_scope=["steel_frame", "internal_roads"],
            ),
            {},
        ),
        (_project(), FIRE_REFS),
        (
            _project(
                title="Residential Advisory DD",
                building_class="residential",
                work_type="advisory",
                subclasses=["house"],
                scale={"gfa_sqm": 260},
                complexity={},
                work_scope=["technical_dd"],
            ),
            {},
        ),
    ],
)
def test_taxonomy_matrix_scaffolds_obey_primary_contract(project, seed_refs) -> None:
    markdown = render_pmp_scaffold(
        project,
        MobilisationEvidencePack(),
        "platform_seeded",
        seed_section_refs=seed_refs,
    )
    context = pmp_taxonomy_context(project)
    assert context is not None
    headings = markdown_section_headings(markdown)

    assert headings == list(required_section_headings(project=project))
    assert headings[-1] == "Citation key"
    assert "| Field | Project detail | Citation |" not in markdown
    assert "| Expected consultants |" not in markdown
    assert _min_words(project) <= pmp_word_count(markdown) <= _max_words(project) * 1.05
    assert "Grounded" not in markdown
    assert markdown.count("```pmp-decision") >= 4
    assert _risk_table_row_count(markdown) <= 8

    top_section_id = max(
        (
            (section_id, weight)
            for section_id, weight in context.section_weights.items()
            if section_id not in {"snapshot", "citation-key"}
        ),
        key=lambda item: item[1],
    )[0]
    top_heading = heading_for_section_id(top_section_id, work_type=context.work_type)
    counts = dict(_section_word_counts(markdown))
    top_count = counts[top_heading]
    assert all(
        top_count >= count
        for heading, count in counts.items()
        if heading not in {"Project Summary", "Citation key"}
    )

    if context.work_scope:
        assert "## Consultants" in markdown
    if "fire_services" in context.work_scope:
        assert "AS 2419.1" in markdown
        assert "AS 2941" in markdown
        assert "seed/as-standards-reference.md#as-2419" in markdown
        assert "Fire Engineer" in _section_body(markdown, "Consultants")
    if context.building_class == "commercial":
        assert "BASIX" not in markdown
        assert "HBCF" not in markdown


def _section_word_counts(markdown: str) -> list[tuple[str, int]]:
    from app.sitewise.markdown_sections import split_sections
    from app.sitewise.pmp_length import pmp_word_count as count

    return [
        (section.heading, count(section.content))
        for section in split_sections(markdown)
        if section.level == 2
    ]


def _section_body(markdown: str, heading: str) -> str:
    from app.sitewise.markdown_sections import split_sections

    for section in split_sections(markdown):
        if section.level == 2 and section.heading == heading:
            return section.content
    return ""


def _risk_table_row_count(markdown: str) -> int:
    in_risks = False
    count = 0
    for line in markdown.splitlines():
        if line.startswith("## Risks and mitigations"):
            in_risks = True
            continue
        if in_risks and line.startswith("## "):
            break
        if in_risks and line.startswith("|") and not line.startswith("| ---") and "Risk |" not in line:
            count += 1
    return count
