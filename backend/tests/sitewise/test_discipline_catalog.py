from types import SimpleNamespace

from app.sitewise.discipline_catalog import (
    discipline_by_code,
    discipline_catalog,
    required_project_disciplines,
    resolve_discipline,
)
from app.sitewise.taxonomy import work_types, work_scope_options_for
from app.workflows.consultant_procurement import DISCIPLINE_PROFILES
from app.workflows.trade_procurement import TRADE_PACKAGES


def test_catalogue_codes_and_aliases_are_validated() -> None:
    entries = discipline_catalog()

    assert len(entries) == len({entry.code for entry in entries})
    assert resolve_discipline(
        "structural engineer", participant_type="consultant"
    ).code == "consultant.structural"
    assert resolve_discipline(
        "electrical contractor", participant_type="trade"
    ).code == "trade.electrical"


def test_procurement_picker_uses_concise_consultant_labels() -> None:
    entries = {entry.code: entry for entry in discipline_catalog()}

    assert {
        code
        for code, entry in entries.items()
        if entry.participant_type == "consultant" and not entry.picker_visible
    } == {
        "consultant.building",
        "consultant.commissioning",
        "consultant.construction_manager",
        "consultant.demolition",
        "consultant.expert_witness",
        "consultant.specialist",
    }
    assert {
        code: entries[code].label
        for code in (
            "consultant.environmental",
            "consultant.hazmat",
            "consultant.programming",
            "consultant.security",
            "consultant.vertical_transport",
            "consultant.waterproofing",
        )
    } == {
        "consultant.environmental": "Environmental",
        "consultant.hazmat": "Hazmat",
        "consultant.programming": "Programmer",
        "consultant.security": "Security",
        "consultant.vertical_transport": "Vertical Transport",
        "consultant.waterproofing": "Waterproofing",
    }
    assert resolve_discipline("Environmental Consultant").label == "Environmental"
    assert resolve_discipline("Programming Consultant").label == "Programmer"


def test_civil_and_stormwater_pmp_label_resolves_to_civil() -> None:
    assert (
        resolve_discipline("civil & stormwater", participant_type="consultant").code
        == "consultant.civil"
    )


def test_every_work_scope_and_workflow_profile_uses_catalogue_identity() -> None:
    for work_type in work_types():
        for item in work_scope_options_for(work_type.value):
            for label in item.consultants:
                assert resolve_discipline(label)

    for profile in DISCIPLINE_PROFILES.values():
        assert profile.discipline_code is not None
        assert discipline_by_code(profile.discipline_code)
    for profile in TRADE_PACKAGES.values():
        assert profile.discipline_code is not None
        assert discipline_by_code(profile.discipline_code)


def test_house_roster_is_shared_and_stably_coded() -> None:
    project = SimpleNamespace(
        building_class="residential",
        work_type="new",
        archetype=None,
        project_metadata={
            "taxonomy": {
                "subclasses": ["house"],
                "work_scope": [],
            }
        },
    )

    rows = required_project_disciplines(project)

    assert [row.code for row in rows] == [
        "consultant.architect",
        "consultant.civil",
        "consultant.structural",
        "consultant.town_planner",
    ]
    assert all(row.sources == ("typical",) for row in rows)


def test_participant_type_keeps_similar_commercial_scopes_distinct() -> None:
    assert (
        resolve_discipline("Electrical", participant_type="consultant").code
        == "consultant.electrical"
    )
    assert (
        resolve_discipline("Electrical Services", participant_type="trade").code
        == "trade.electrical"
    )
