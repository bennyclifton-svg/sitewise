from datetime import date

import pytest
from pydantic import ValidationError

from app.programme.schemas import (
    MAX_PROGRAMME_OPERATIONS,
    ProgrammeActivityInput,
    ProgrammeOperation,
    ProgrammeOperationsBatch,
    ProgrammeState,
    ProgrammeViewUpdate,
)

PROJECT_ID = "10000000-0000-0000-0000-000000000001"


def _stage(**updates) -> dict:
    values = {
        "activity_key": "planning",
        "kind": "stage",
        "name": "Planning",
        "start_date": date(2026, 8, 16),
        "duration_days": 90,
    }
    values.update(updates)
    return values


def test_activity_input_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProgrammeActivityInput(**_stage(), unknown="x")


def test_stage_cannot_have_parent() -> None:
    with pytest.raises(ValidationError, match="parent_key"):
        ProgrammeActivityInput(**_stage(parent_key="other"))


def test_activity_requires_parent() -> None:
    with pytest.raises(ValidationError, match="parent_key"):
        ProgrammeActivityInput(
            activity_key="slab",
            kind="activity",
            name="Slab",
            start_date=date(2026, 2, 1),
            duration_days=14,
        )


def test_milestone_duration_must_be_zero() -> None:
    with pytest.raises(ValidationError, match="duration_days"):
        ProgrammeActivityInput(
            activity_key="da",
            kind="milestone",
            parent_key="planning",
            name="DA lodgement",
            start_date=date(2026, 9, 1),
            duration_days=1,
        )


def test_add_and_update_require_values() -> None:
    with pytest.raises(ValidationError, match="values"):
        ProgrammeOperation(operation="ADD", target_type="stage")
    with pytest.raises(ValidationError, match="values"):
        ProgrammeOperation(
            operation="UPDATE",
            target_type="stage",
            target_id="planning",
        )


def test_operation_accepts_flattened_activity_fields() -> None:
    operation = ProgrammeOperation.model_validate(
        {
            "operation": "ADD",
            "target_type": "activity",
            "name": "Concept design",
            "parent_key": "planning",
            "start_date": "2026-08-16",
            "duration_days": 42,
            "predecessor_key": "brief",
        }
    )
    assert operation.values["name"] == "Concept design"
    assert operation.values["parent_key"] == "planning"
    assert operation.values["duration_days"] == 42
    assert operation.values["predecessor_key"] == "brief"


def test_operation_accepts_artefact_style_target() -> None:
    operation = ProgrammeOperation.model_validate(
        {
            "operation": "ADD",
            "target": {"type": "activity"},
            "values": {
                "name": "DA lodgement",
                "parent_key": "planning",
                "start_date": "2026-09-01",
                "duration_days": 0,
                "kind": "milestone",
            },
        }
    )
    assert operation.target_type == "activity"
    assert operation.values["name"] == "DA lodgement"


def test_non_add_requires_target_id() -> None:
    with pytest.raises(ValidationError, match="target_id"):
        ProgrammeOperation(
            operation="DELETE",
            target_type="stage",
        )


def test_move_requires_reference_and_placement() -> None:
    with pytest.raises(ValidationError, match="reference_id"):
        ProgrammeOperation(
            operation="MOVE",
            target_type="activity",
            target_id="slab",
        )


def test_valid_operation_and_state() -> None:
    operation = ProgrammeOperation(
        operation="ADD",
        target_type="activity",
        values={
            "activity_key": "slab",
            "name": "Slab",
            "parent_key": "delivery",
            "start_date": "2026-02-01",
            "duration_days": 14,
        },
    )
    state = ProgrammeState(
        project_id=PROJECT_ID,
        version=1,
        activities=[ProgrammeActivityInput(**_stage())],
    )
    assert operation.target_type == "activity"
    assert state.view_scale == "month"
    assert state.pmp_embed_visible is True


def test_operations_batch_rejects_more_than_eighty() -> None:
    operations = [
        ProgrammeOperation(
            operation="ADD",
            target_type="activity",
            values={
                "activity_key": f"a{index}",
                "name": f"A{index}",
                "parent_key": "delivery",
                "start_date": "2026-02-01",
                "duration_days": 1,
            },
        )
        for index in range(MAX_PROGRAMME_OPERATIONS + 1)
    ]
    with pytest.raises(ValidationError, match="80"):
        ProgrammeOperationsBatch(operations=operations)


def test_view_update_requires_a_field() -> None:
    with pytest.raises(ValidationError, match="required"):
        ProgrammeViewUpdate()
    update = ProgrammeViewUpdate(view_scale="quarter")
    assert update.view_scale == "quarter"
