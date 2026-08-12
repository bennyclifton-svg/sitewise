"""The design lead follows the dominant scope, not a hardcoded Architect.

Wave 1 named an Architect as design lead on all four PMPs, including a
mechanical plant replacement and a lift replacement. The row was appended
unconditionally before the scope-derived consultant loop ran, so it was the
entire register whenever work_scope was empty.
"""

from types import SimpleNamespace

from app.sitewise.pmp_renderer import _render_taxonomy_consultants
from app.sitewise.taxonomy import design_lead_discipline


def _project(work_scope: list[str], work_type: str = "refurb"):
    return SimpleNamespace(
        title="Test",
        archetype=None,
        building_class="commercial",
        work_type=work_type,
        state="NSW",
        project_metadata={
            "taxonomy": {"subclasses": ["office"], "work_scope": work_scope}
        },
    )


def test_mechanical_scope_leads_with_a_services_engineer() -> None:
    assert design_lead_discipline("refurb", ["mechanical_hvac"]) == (
        "Services Engineer (Mechanical)"
    )


def test_electrical_scope_leads_with_an_electrical_engineer() -> None:
    assert design_lead_discipline("refurb", ["electrical_power"]) == (
        "Services Engineer (Electrical)"
    )


def test_fitout_scope_still_leads_with_the_architect() -> None:
    assert design_lead_discipline("refurb", ["partitions_walls"]) == "Architect"


def test_no_scope_falls_back_to_the_architect() -> None:
    assert design_lead_discipline("refurb", []) == "Architect"
    assert design_lead_discipline(None, []) == "Architect"


def test_rendered_register_leads_with_the_resolved_discipline() -> None:
    markdown = _render_taxonomy_consultants(_project(["mechanical_hvac"]))
    rows = [line for line in markdown.splitlines() if line.startswith("| ")]
    disciplines = [row.split("|")[1].strip() for row in rows[2:]]

    assert disciplines[0] == "Services Engineer (Mechanical)"
    assert "Architect" not in disciplines
    assert "The Services Engineer (Mechanical) row is the design lead" in markdown


def test_architect_is_not_duplicated_when_it_is_the_lead() -> None:
    markdown = _render_taxonomy_consultants(_project(["partitions_walls"]))
    rows = [line for line in markdown.splitlines() if line.startswith("| ")]
    disciplines = [row.split("|")[1].strip() for row in rows[2:]]

    assert disciplines[0] == "Architect"
    assert disciplines.count("Architect") == 1
