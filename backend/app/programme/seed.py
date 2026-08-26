from __future__ import annotations

from datetime import date

from app.programme.mutate import dependency_key
from app.programme.schemas import ProgrammeActivityInput, ProgrammeDependencyInput

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
            assumption=True,
        )
        for index, (key, name, duration_days, predecessor) in enumerate(DEFAULT_STAGES)
    ]


def default_dependencies() -> list[ProgrammeDependencyInput]:
    return [
        ProgrammeDependencyInput(
            dependency_key=dependency_key(predecessor, "finish", key, "start"),
            source_activity_key=predecessor,
            target_activity_key=key,
            source_endpoint="finish",
            target_endpoint="start",
            lag_days=0,
        )
        for key, _name, _duration_days, predecessor in DEFAULT_STAGES
        if predecessor is not None
    ]
