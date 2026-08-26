from datetime import date
from uuid import UUID

from app.programme.figure import FIGURE_WIDTH, render_programme_svg
from app.programme.schemas import (
    ProgrammeActivityInput,
    ProgrammeDependencyInput,
    ProgrammeState,
)

PROJECT_ID = UUID("10000000-0000-0000-0000-000000000001")


def _state(*names: str) -> ProgrammeState:
    return ProgrammeState(
        project_id=PROJECT_ID,
        version=1,
        view_scale="month",
        activities=[
            ProgrammeActivityInput(
                activity_key=name.lower(),
                kind="stage",
                name=name,
                display_order=index,
                start_date=date(2026, 8, 16),
                duration_days=90,
                finish_date=date(2026, 11, 14),
            )
            for index, name in enumerate(names)
        ],
    )


def test_figure_is_fitted_svg() -> None:
    svg = render_programme_svg(_state("Planning", "Procurement", "Delivery"))
    assert svg.startswith("<svg")
    assert f'width="{FIGURE_WIDTH}"' in svg
    assert "Planning" in svg
    assert "Procurement" in svg
    assert "Delivery" in svg
    assert "<script" not in svg


def test_figure_escapes_activity_names() -> None:
    svg = render_programme_svg(_state('DA <hold> & "gate"'))
    assert "<hold>" not in svg
    assert "&amp;" in svg or "&quot;" in svg or "DA" in svg


def test_figure_routes_typed_dependencies_behind_bars() -> None:
    state = _state("Planning", "Procurement")
    state.dependencies = [
        ProgrammeDependencyInput(
            dependency_key="planning:start->procurement:finish",
            source_activity_key="planning",
            target_activity_key="procurement",
            source_endpoint="start",
            target_endpoint="finish",
            lag_days=3,
        )
    ]
    svg = render_programme_svg(state)
    assert 'marker-end="url(#dependency-arrow)"' in svg
    assert " V 82.0 " in svg


def test_figure_uses_summary_brackets_and_hides_collapsed_children() -> None:
    state = _state("Planning")
    state.activities.append(
        ProgrammeActivityInput(
            activity_key="concept-design",
            kind="activity",
            parent_key="planning",
            name="Concept design",
            display_order=1,
            start_date=date(2026, 8, 16),
            duration_days=30,
            finish_date=date(2026, 9, 15),
        )
    )
    expanded = render_programme_svg(state)
    assert "Concept design" in expanded
    assert "<path" in expanded
    assert 'rx="1"' in expanded

    state.collapsed_stage_keys = ["planning"]
    collapsed = render_programme_svg(state)
    assert "Planning" in collapsed
    assert "Concept design" not in collapsed
