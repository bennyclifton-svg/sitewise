from __future__ import annotations

from datetime import date

from app.programme.schemas import ProgrammeActivityInput

DEFAULT_STAGES: tuple[tuple[str, str, int, str | None], ...] = (
    ("planning", "Planning", 90, None),
    ("procurement", "Procurement", 60, "planning"),
    ("delivery", "Delivery", 365, "procurement"),
)


def default_stage_inputs(*, start: date) -> list[ProgrammeActivityInput]:
    return [
        ProgrammeActivityInput(
            activity_key=key,
            kind="stage",
            name=name,
            display_order=index,
            start_date=start,
            duration_days=duration_days,
            predecessor_key=predecessor,
            assumption=True,
        )
        for index, (key, name, duration_days, predecessor) in enumerate(DEFAULT_STAGES)
    ]
