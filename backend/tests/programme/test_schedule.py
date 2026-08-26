from datetime import date

import pytest

from app.programme.schedule import (
    ActivityDraft,
    DependencyDraft,
    rollup_stages,
    schedule_activities,
)


def test_finish_is_start_plus_duration_days() -> None:
    rows = schedule_activities(
        [
            ActivityDraft(
                activity_key="planning",
                kind="stage",
                start_date=date(2026, 8, 16),
                duration_days=90,
            )
        ]
    )
    assert rows[0].finish_date == date(2026, 11, 14)


def test_milestone_finish_equals_start() -> None:
    rows = schedule_activities(
        [
            ActivityDraft(
                activity_key="da",
                kind="milestone",
                start_date=date(2026, 9, 1),
                duration_days=0,
            )
        ]
    )
    assert rows[0].finish_date == date(2026, 9, 1)


def test_linked_successor_starts_at_predecessor_finish_plus_lag() -> None:
    rows = schedule_activities(
        [
            ActivityDraft(
                activity_key="planning",
                kind="stage",
                start_date=date(2026, 8, 16),
                duration_days=90,
            ),
            ActivityDraft(
                activity_key="procurement",
                kind="stage",
                start_date=date(2026, 1, 1),
                duration_days=60,
            ),
        ],
        [
            DependencyDraft(
                dependency_key="planning:finish->procurement:start",
                source_activity_key="planning",
                target_activity_key="procurement",
                source_endpoint="finish",
                target_endpoint="start",
            )
        ],
    )
    by_key = {row.activity_key: row for row in rows}
    assert by_key["procurement"].start_date == date(2026, 11, 14)


def test_floating_activity_keeps_its_start() -> None:
    rows = schedule_activities(
        [
            ActivityDraft(
                activity_key="planning",
                kind="stage",
                start_date=date(2026, 8, 16),
                duration_days=90,
            ),
            ActivityDraft(
                activity_key="long-lead",
                kind="activity",
                parent_key="planning",
                start_date=date(2026, 7, 1),
                duration_days=30,
            ),
        ]
    )
    assert rows[1].start_date == date(2026, 7, 1)


@pytest.mark.parametrize(
    ("source_endpoint", "target_endpoint", "expected_start"),
    [
        ("start", "start", date(2026, 8, 21)),
        ("start", "finish", date(2026, 8, 11)),
        ("finish", "finish", date(2026, 8, 21)),
        ("finish", "start", date(2026, 8, 31)),
    ],
)
def test_schedules_all_four_relationships(
    source_endpoint: str,
    target_endpoint: str,
    expected_start: date,
) -> None:
    rows = schedule_activities(
        [
            ActivityDraft("source", "activity", date(2026, 8, 16), 10),
            ActivityDraft("target", "activity", date(2026, 1, 1), 10),
        ],
        [
            DependencyDraft(
                dependency_key="link",
                source_activity_key="source",
                target_activity_key="target",
                source_endpoint=source_endpoint,  # type: ignore[arg-type]
                target_endpoint=target_endpoint,  # type: ignore[arg-type]
                lag_days=5,
            )
        ],
    )
    assert rows[1].start_date == expected_start


def test_stage_rollup_uses_children() -> None:
    rows = rollup_stages(
        schedule_activities(
            [
                ActivityDraft(
                    activity_key="delivery",
                    kind="stage",
                    start_date=date(2026, 1, 1),
                    duration_days=10,
                ),
                ActivityDraft(
                    activity_key="slab",
                    kind="activity",
                    parent_key="delivery",
                    start_date=date(2026, 2, 1),
                    duration_days=14,
                ),
                ActivityDraft(
                    activity_key="frame",
                    kind="activity",
                    parent_key="delivery",
                    start_date=date(2026, 2, 20),
                    duration_days=21,
                ),
            ]
        )
    )
    delivery = next(row for row in rows if row.activity_key == "delivery")
    assert delivery.start_date == date(2026, 2, 1)
    assert delivery.finish_date == date(2026, 3, 13)


def test_cycle_detection_raises() -> None:
    with pytest.raises(ValueError, match="cycle"):
        schedule_activities(
            [
                ActivityDraft(
                    activity_key="planning",
                    kind="stage",
                    start_date=date(2026, 8, 16),
                    duration_days=90,
                ),
                ActivityDraft(
                    activity_key="procurement",
                    kind="stage",
                    start_date=date(2026, 11, 14),
                    duration_days=60,
                ),
            ],
            [
                DependencyDraft("one", "planning", "procurement", "finish", "start"),
                DependencyDraft("two", "procurement", "planning", "finish", "start"),
            ],
        )


def test_missing_predecessor_raises() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        schedule_activities(
            [
                ActivityDraft(
                    activity_key="procurement",
                    kind="stage",
                    start_date=date(2026, 8, 16),
                    duration_days=60,
                )
            ],
            [
                DependencyDraft("missing", "planning", "procurement", "finish", "start")
            ],
        )


def test_negative_duration_raises() -> None:
    with pytest.raises(ValueError, match="negative"):
        schedule_activities(
            [
                ActivityDraft(
                    activity_key="planning",
                    kind="stage",
                    start_date=date(2026, 8, 16),
                    duration_days=-1,
                )
            ]
        )


def test_milestone_with_duration_raises() -> None:
    with pytest.raises(ValueError, match="milestone"):
        schedule_activities(
            [
                ActivityDraft(
                    activity_key="da",
                    kind="milestone",
                    start_date=date(2026, 9, 1),
                    duration_days=1,
                )
            ]
        )
