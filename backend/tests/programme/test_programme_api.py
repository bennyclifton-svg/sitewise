from datetime import date

import pytest
from pydantic import ValidationError

from app.programme.schemas import ProgrammeOperation
from app.schemas.projects import (
    ApplyProgrammeOperationsRequest,
    SetProgrammeViewRequest,
)


def test_operations_request_caps_at_eighty() -> None:
    operations = [
        ProgrammeOperation(
            operation="ADD",
            target_type="activity",
            values={
                "name": f"A{index}",
                "parent_key": "delivery",
                "start_date": date(2026, 2, 1),
                "duration_days": 1,
            },
        )
        for index in range(81)
    ]
    with pytest.raises(ValidationError):
        ApplyProgrammeOperationsRequest(
            expected_base_version=1,
            operations=operations,
        )


def test_view_request_requires_a_field() -> None:
    with pytest.raises(ValidationError):
        SetProgrammeViewRequest(expected_base_version=1)
    body = SetProgrammeViewRequest(
        expected_base_version=2,
        view_scale="week",
    )
    assert body.view_scale == "week"
