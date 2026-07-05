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
    user_role: str = "architect-pm",
):
    return SimpleNamespace(
        slug=title.lower().replace(" ", "-"),
        title=title,
        workspace_path=f"04-projects/{title.lower().replace(' ', '-')}",
        phase="brief-planning",
        archetype=None,
        building_class=building_class,
        work_type=work_type,
        user_role=user_role,
        state="NSW",
        project_metadata={
            "taxonomy": {
                "subclasses": subclasses or ["office"],
                "scale": scale or {"nla_sqm": 1200, "storeys": 3},
                "complexity": complexity or {"operational_constraints": "live_environment"},
                "work_scope": work_scope or ["fire_services"],
                "budget": "$1,000,000",
            }
        },
    )


def test_adaptive_greenfield_contract_has_budgets_and_fire_as_refs() -> None:
    project = _project()
    context = pmp_taxonomy_context(project)
    assert context is not None
    target_words = (settings.pmp_min_words + settings.pmp_max_words) // 2

    brief = build_greenfield_brief(
        archetype="",
        user_role="architect-pm",
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

    assert "Compliance and approvals (~" in brief
    assert "AS 2419.1 hydrant systems" in brief
    assert "AS 2941 pumpsets" in brief
    assert FIRE_REFS["compliance-approvals"][0] in brief
    assert "Fire Services" in brief
    assert "consultants Fire Engineer" in brief

    budgets = []
    for line in brief.splitlines():
        if "(~" not in line or " words)" not in line:
            continue
        budgets.append(int(line.split("(~", 1)[1].split(" words)", 1)[0]))
    assert abs(sum(budgets) - target_words) <= len(budgets)


def test_taxonomy_platform_seeded_scaffold_has_universal_sections_and_provenance() -> None:
    project = _project()
    markdown = render_pmp_scaffold(
        project,
        MobilisationEvidencePack(),
        "platform_seeded",
        seed_section_refs=FIRE_REFS,
    )

    assert markdown_section_headings(markdown) == list(
        required_section_headings("architect-pm", project=project)
    )
    assert settings.pmp_min_words <= pmp_word_count(markdown) <= settings.pmp_max_words * 1.05
    assert "User provided" in markdown
    assert "Assumption" in markdown
    assert "Not evidenced" in markdown
    assert "Grounded" not in markdown
    assert markdown.count("```pmp-decision") >= 4
    assert length_violations(
        markdown,
        weights=pmp_taxonomy_context(project).section_weights,
        min_words=settings.pmp_min_words,
        max_words=settings.pmp_max_words,
    ) == []


def test_commercial_fire_scaffold_is_compliance_heavy_and_not_residential() -> None:
    project = _project()
    markdown = render_pmp_scaffold(
        project,
        MobilisationEvidencePack(),
        "platform_seeded",
        seed_section_refs=FIRE_REFS,
    )
    counts = dict(_section_word_counts(markdown))

    assert counts["Compliance and approvals"] > counts["Scope and client requirements"]
    assert counts["Compliance and approvals"] > counts["Risks and mitigations"]
    assert "AS 2419.1" in markdown
    assert "AS 2941" in markdown
    assert "Fire Engineer" in markdown
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

    assert counts["Scope and client requirements"] > counts["Compliance and approvals"]
    assert counts["Scope and client requirements"] > counts["Risks and mitigations"]
    assert "finishes" in markdown.lower()
    assert "fixtures" in markdown.lower()
    assert "owner selections" in markdown.lower()


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
                user_role="d-and-c",
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

    assert markdown_section_headings(markdown) == list(
        required_section_headings(project.user_role, project=project)
    )
    assert settings.pmp_min_words <= pmp_word_count(markdown) <= settings.pmp_max_words * 1.05
    assert "Grounded" not in markdown
    assert markdown.count("```pmp-decision") >= 4
    assert _risk_table_row_count(markdown) <= 8

    top_section_id = max(
        (
            (section_id, weight)
            for section_id, weight in context.section_weights.items()
            if section_id != "snapshot"
        ),
        key=lambda item: item[1],
    )[0]
    top_heading = heading_for_section_id(top_section_id, work_type=context.work_type)
    counts = dict(_section_word_counts(markdown))
    top_count = counts[top_heading]
    assert all(
        top_count >= count
        for heading, count in counts.items()
        if heading != "Project snapshot"
    )

    if context.work_scope:
        assert "consultants" in markdown.lower()
    if "fire_services" in context.work_scope:
        assert "AS 2419.1" in markdown
        assert "AS 2941" in markdown
        assert "seed/as-standards-reference.md#as-2419" in markdown
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
