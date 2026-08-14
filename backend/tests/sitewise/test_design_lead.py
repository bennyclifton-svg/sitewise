"""The design lead follows the dominant design discipline, not file order.

Wave 1 named an Architect as design lead on all four PMPs. Wave 2 still named
Building Consultant or Project Manager whenever those roles appeared first in
work-scopes.json, because work_scope_items_for reorders selection into
declaration order. Project Manager, Building Consultant, Commissioning Agent,
and Building Certifier may sit on the register but must never be the lead.
"""

from types import SimpleNamespace

from app.sitewise.pmp_greenfield_brief import _contract_focus_line
from app.sitewise.pmp_renderer import _render_taxonomy_consultants
from app.sitewise.taxonomy import design_lead_discipline, non_design_consultants


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


def test_no_scope_is_to_be_confirmed_not_architect() -> None:
    assert design_lead_discipline("refurb", []) == "to be confirmed"
    assert design_lead_discipline(None, []) == "to be confirmed"
    assert design_lead_discipline("remediation", []) == "to be confirmed"


def test_services_outrank_condition_assessment_regardless_of_selection_order() -> None:
    assert design_lead_discipline(
        "refurb", ["mechanical_hvac", "building_condition"]
    ) == "Services Engineer (Mechanical)"
    assert design_lead_discipline(
        "refurb", ["building_condition", "mechanical_hvac"]
    ) == "Services Engineer (Mechanical)"


def test_project_manager_is_never_the_design_lead() -> None:
    assert design_lead_discipline(
        "refurb", ["accessibility_upgrade", "live_environment_fitout"]
    ) == "Access Consultant"
    assert design_lead_discipline(
        "refurb", ["live_environment_fitout", "accessibility_upgrade"]
    ) == "Access Consultant"


def test_building_consultant_is_never_the_design_lead() -> None:
    assert design_lead_discipline("refurb", ["building_condition"]) == (
        "to be confirmed"
    )
    assert design_lead_discipline("advisory", ["technical_dd"]) == "Structural Engineer"


def test_vertical_transport_leads_with_the_lift_consultant() -> None:
    assert design_lead_discipline("new", ["vertical_transport"]) == (
        "Vertical Transport Consultant"
    )


def test_facade_remediation_leads_with_the_facade_engineer() -> None:
    assert design_lead_discipline("remediation", ["facade_cladding"]) == (
        "Facade Engineer"
    )


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


def test_empty_scope_register_does_not_invent_an_architect_lead() -> None:
    markdown = _render_taxonomy_consultants(_project([]))
    assert "Design lead — to be confirmed" in markdown
    assert "The Architect row is the design lead" not in markdown
    assert "| Architect |" not in markdown


def test_condition_assessment_stays_on_the_register_but_is_not_the_lead() -> None:
    markdown = _render_taxonomy_consultants(_project(["building_condition"]))
    assert "Design lead — to be confirmed" in markdown
    assert "The Building Consultant row is the design lead" not in markdown
    assert "| Building Consultant |" in markdown


def test_consultants_brief_leads_with_the_resolved_discipline_not_architect() -> None:
    line = _contract_focus_line(
        "consultants",
        work_type="refurb",
        work_scope=("mechanical_hvac",),
        refs=(),
    )
    assert "Services Engineer (Mechanical) first" in line
    assert "Architect first" not in line


def test_consultants_brief_does_not_keep_architect_first_when_scope_is_empty() -> None:
    line = _contract_focus_line(
        "consultants",
        work_type="refurb",
        work_scope=(),
        refs=(),
    )
    assert "Architect first" not in line
    assert "to be confirmed" in line.lower()


def test_non_design_consultants_cannot_be_named_as_lead() -> None:
    assert {
        "project manager",
        "building consultant",
        "commissioning agent",
        "building certifier",
    } <= non_design_consultants()
