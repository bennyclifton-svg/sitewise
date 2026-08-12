"""The user's own scope wording reaching the rendered PMP.

Wave 2's remediation, extension and rail runs each captured a correct
classification and then produced a document that never named the work. The
enum labels rendered instead — "Facade/Cladding Rectification", "Live
Environment Fitout" — which are routing keys that happen to be printable, not
descriptions a client recognises.
"""

from types import SimpleNamespace

from app.sitewise.pmp_renderer import (
    _render_taxonomy_scope,
    _taxonomy_project_description,
)

CONCRETE_CANCER = "Concrete cancer remediation to basement carpark slab and columns"
FACADE_SPALLING = "Spalling repair to eastern facade"


def _project(
    *,
    work_scope: list[str] | None = None,
    scope_narrative: list[str] | None = None,
    work_type: str = "remediation",
    building_class: str = "residential",
    subclasses: list[str] | None = None,
):
    taxonomy: dict = {"subclasses": subclasses or ["apartments"]}
    if work_scope is not None:
        taxonomy["work_scope"] = work_scope
    if scope_narrative is not None:
        taxonomy["scope_narrative"] = scope_narrative
    return SimpleNamespace(
        title="Remedial concrete and facade",
        building_class=building_class,
        work_type=work_type,
        state="NSW",
        project_metadata={"taxonomy": taxonomy},
    )


def test_narrative_items_render_as_scope_inclusions() -> None:
    scope = _render_taxonomy_scope(
        _project(scope_narrative=[CONCRETE_CANCER, FACADE_SPALLING])
    )

    assert f"- {CONCRETE_CANCER}" in scope
    assert f"- {FACADE_SPALLING}" in scope


def test_narrative_does_not_replace_the_enum_labels() -> None:
    """Both belong in the brief: the enum says which doctrine applies."""
    scope = _render_taxonomy_scope(
        _project(
            work_scope=["facade_cladding"],
            scope_narrative=[CONCRETE_CANCER],
        )
    )

    assert "Facade/Cladding Rectification" in scope
    assert f"- {CONCRETE_CANCER}" in scope


def test_narrative_alone_replaces_the_scope_pending_placeholder() -> None:
    """A described job is not a job with no scope, even when no enum value fits.

    `remediation` offers no structural-repair scope value, so concrete cancer
    cannot be expressed as an enum at all. The document must still say what the
    work is rather than "Scope selection pending".
    """
    scope = _render_taxonomy_scope(_project(scope_narrative=[CONCRETE_CANCER]))

    assert "Scope selection pending" not in scope
    assert CONCRETE_CANCER in scope


def test_no_scope_at_all_still_reaches_the_placeholder() -> None:
    scope = _render_taxonomy_scope(_project())

    assert "Scope selection pending" in scope


def test_description_leads_with_the_users_wording_not_the_enum_label() -> None:
    description = _taxonomy_project_description(
        _project(
            work_scope=["facade_cladding"],
            scope_narrative=[CONCRETE_CANCER, FACADE_SPALLING],
        )
    )

    assert CONCRETE_CANCER in description
    assert FACADE_SPALLING in description
    assert "Facade/Cladding Rectification" not in description


def test_description_falls_back_to_enum_labels_without_a_narrative() -> None:
    description = _taxonomy_project_description(_project(work_scope=["facade_cladding"]))

    assert "Facade/Cladding Rectification" in description


def test_description_stops_claiming_scope_is_not_stated_when_it_is() -> None:
    """Three Wave 2 documents opened by denying facts the prompt had supplied."""
    described = _taxonomy_project_description(_project(scope_narrative=[CONCRETE_CANCER]))
    undescribed = _taxonomy_project_description(_project())

    assert "remain to be confirmed" not in described
    assert "remain to be confirmed" in undescribed


def test_rail_station_scope_survives_into_the_brief() -> None:
    """Prompt 61 lost lifts, footbridge, platforms and canopies at 2/7 retention."""
    scope = _render_taxonomy_scope(
        _project(
            building_class="infrastructure",
            subclasses=["rail_metro"],
            work_type="refurb",
            work_scope=["accessibility_upgrade"],
            scope_narrative=[
                "New lifts to both platforms",
                "New footbridge",
                "Accessible platform upgrades and new canopies",
                "Work in track possessions with the line operational",
            ],
        )
    )

    for fact in ("lifts", "footbridge", "canopies", "possessions"):
        assert fact in scope, fact
