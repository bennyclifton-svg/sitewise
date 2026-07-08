import uuid

import pytest
from pydantic import ValidationError

from tender.schemas import ComparisonCreate, ProjectContext


def _context_payload(**overrides) -> dict:
    payload = {
        "state": "NSW",
        "region": "metro",
        "build_type": "new_build",
        "dwelling_class": "class_1a",
        "storeys": 2,
        "floor_area_m2": 220.5,
        "site_area_m2": 450.0,
        "soil_class": "M",
        "slope_class": "moderate",
        "bal_rating": "12.5",
        "wind_rating": "N2",
        "flood_overlay": False,
        "heritage_overlay": None,
        "existing_dwelling_era": None,
        "demolition_required": False,
        "spec_level": "mid",
        "target_budget_cents": 95_000_000,
        "notes": "steep rear yard",
    }
    payload.update(overrides)
    return payload


def test_project_context_round_trips() -> None:
    context = ProjectContext.model_validate(_context_payload())
    assert ProjectContext.model_validate(context.model_dump()) == context


def test_project_context_version_defaults_to_1() -> None:
    context = ProjectContext.model_validate(_context_payload())
    assert context.context_version == 1


def test_project_context_allows_repository_selection_without_manual_fields() -> None:
    context = ProjectContext.model_validate(
        {
            "context_version": 1,
            "context_source": "repository_selection",
        }
    )

    assert context.context_source == "repository_selection"
    assert context.state is None
    assert context.region is None
    assert context.build_type is None
    assert context.storeys is None
    assert context.spec_level is None


def test_project_context_rejects_bad_soil_class() -> None:
    with pytest.raises(ValidationError):
        ProjectContext.model_validate(_context_payload(soil_class="Z9"))


def test_project_context_rejects_bad_bal_rating() -> None:
    with pytest.raises(ValidationError):
        ProjectContext.model_validate(_context_payload(bal_rating="100"))


def test_comparison_create_validates_nested_context() -> None:
    request = ComparisonCreate(
        project_id=uuid.uuid4(), context=_context_payload()
    )
    assert request.context.soil_class == "M"

    with pytest.raises(ValidationError):
        ComparisonCreate(
            project_id=uuid.uuid4(), context=_context_payload(spec_level="luxury")
        )
