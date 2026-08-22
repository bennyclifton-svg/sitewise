"""The asset register reaching the rendered PMP.

Wave 1's mechanical prompt scored 0/7 on fact retention and rendered an FFE
Schedule containing one placeholder row — on a plant replacement with no
finishes to schedule. The equipment being replaced is the schedule that job
needs, and it carries the make, capacity, age and refrigerant the PM supplied.
"""

from types import SimpleNamespace

from app.sitewise.pmp_renderer import _asset_schedule_rows

AC_UNITS = {
    "type": "Split ducted air conditioning system",
    "count": 2,
    "location": "Service centre; western office",
    "make_model": "Pioneer",
    "capacity": "30kW",
    "age_years": 30,
    "condition": "beyond_economical_repair",
    "action": "replace",
    "replacement_spec": "Actron 30kW split ducted",
    "notes": "R22 refrigerant; phase-out obligations apply",
}


def _project(assets: list[dict] | None = None):
    taxonomy: dict = {
        "subclasses": ["office"],
        "work_scope": ["mechanical_hvac"],
    }
    if assets is not None:
        taxonomy["assets"] = assets
    return SimpleNamespace(
        title="Mechanical plant replacement",
        building_class="commercial",
        work_type="refurb",
        state="NSW",
        project_metadata={"taxonomy": taxonomy},
    )


def test_asset_rows_carry_the_facts_the_prompt_supplied() -> None:
    rows = _asset_schedule_rows(_project([AC_UNITS]))

    assert len(rows) == 1
    row = rows[0]
    for fact in (
        "Split ducted air conditioning system",
        "Service centre; western office",
        "30kW",
        "Replace",
        "30 years old",
        "Actron 30kW split ducted",
        "R22",
    ):
        assert fact in row, fact
    assert "2 units" in row
    assert "| Qty |" not in row


def test_a_sparse_asset_still_renders() -> None:
    rows = _asset_schedule_rows(_project([{"type": "Passenger lift"}]))

    assert len(rows) == 1
    assert "Passenger lift" in rows[0]
    assert "User provided" not in rows[0]
    assert "| TBC |" in rows[0]


def test_no_assets_renders_no_rows() -> None:
    assert _asset_schedule_rows(_project()) == []
    assert _asset_schedule_rows(_project([])) == []
