from datetime import date

from app.programme.mutate import apply_operations
from app.programme.schemas import ProgrammeActivityInput, ProgrammeOperation
from app.programme.seed import default_stage_inputs


def _activity(
    key: str,
    parent: str,
    *,
    name: str | None = None,
    order: int = 0,
) -> ProgrammeActivityInput:
    return ProgrammeActivityInput(
        activity_key=key,
        kind="activity",
        parent_key=parent,
        name=name or key.replace("-", " ").title(),
        display_order=order,
        start_date=date(2026, 8, 16),
        duration_days=14,
    )


def test_add_activity_below_stage_inserts_as_first_child() -> None:
    rows = apply_operations(
        default_stage_inputs(start=date(2026, 8, 16)),
        [
            ProgrammeOperation(
                operation="ADD",
                target_type="activity",
                reference_id="planning",
                placement="after",
                values={
                    "name": "Survey",
                    "parent_key": "planning",
                    "start_date": "2026-08-16",
                    "duration_days": 14,
                },
            )
        ],
    )
    assert [item.activity_key for item in rows] == [
        "planning",
        "survey",
        "procurement",
        "delivery",
    ]
    assert rows[1].parent_key == "planning"


def test_add_ignores_unknown_value_fields() -> None:
    rows = apply_operations(
        default_stage_inputs(start=date(2026, 8, 16)),
        [
            ProgrammeOperation(
                operation="ADD",
                target_type="activity",
                values={
                    "name": "Concept design",
                    "parent_key": "planning",
                    "start_date": "2026-08-16",
                    "duration_days": 42,
                    "phase": "design",
                    "description": "Client workshop",
                    "end_date": "2026-09-27",
                },
            )
        ],
    )
    concept = next(item for item in rows if item.activity_key == "concept-design")
    assert concept.parent_key == "planning"
    assert concept.notes == "Client workshop"
    assert concept.duration_days == 42


def test_add_infers_parent_from_reference_stage() -> None:
    rows = apply_operations(
        default_stage_inputs(start=date(2026, 8, 16)),
        [
            ProgrammeOperation(
                operation="ADD",
                target_type="activity",
                reference_id="delivery",
                placement="after",
                values={
                    "name": "Site establishment",
                    "start_date": "2027-02-01",
                    "duration_days": 14,
                },
            )
        ],
    )
    site = next(item for item in rows if item.activity_key == "site-establishment")
    assert site.parent_key == "delivery"


def test_add_stage_below_inserts_after_the_stage_block() -> None:
    seeded = default_stage_inputs(start=date(2026, 8, 16))
    seeded.append(_activity("survey", "planning", order=1))
    rows = apply_operations(
        seeded,
        [
            ProgrammeOperation(
                operation="ADD",
                target_type="stage",
                reference_id="planning",
                placement="after",
                values={
                    "name": "Approvals",
                    "start_date": "2026-11-14",
                    "duration_days": 30,
                },
            )
        ],
    )
    assert [item.activity_key for item in rows] == [
        "planning",
        "survey",
        "approvals",
        "procurement",
        "delivery",
    ]


def test_move_stage_takes_children() -> None:
    seeded = default_stage_inputs(start=date(2026, 8, 16))
    seeded.append(_activity("survey", "planning", order=1))
    rows = apply_operations(
        seeded,
        [
            ProgrammeOperation(
                operation="MOVE",
                target_type="stage",
                target_id="planning",
                reference_id="delivery",
                placement="after",
            )
        ],
    )
    assert [item.activity_key for item in rows] == [
        "procurement",
        "delivery",
        "planning",
        "survey",
    ]


def test_move_activity_reparents_under_drop_stage() -> None:
    seeded = default_stage_inputs(start=date(2026, 8, 16))
    seeded.append(_activity("survey", "planning", order=1))
    rows = apply_operations(
        seeded,
        [
            ProgrammeOperation(
                operation="MOVE",
                target_type="activity",
                target_id="survey",
                reference_id="delivery",
                placement="after",
            )
        ],
    )
    survey = next(item for item in rows if item.activity_key == "survey")
    assert survey.parent_key == "delivery"
    assert [item.activity_key for item in rows] == [
        "planning",
        "procurement",
        "delivery",
        "survey",
    ]
