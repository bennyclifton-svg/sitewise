from datetime import date
from uuid import UUID

from app.programme.figure import FIGURE_WIDTH, render_programme_svg
from app.programme.schemas import ProgrammeActivityInput, ProgrammeState

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
