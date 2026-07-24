import pytest

from app.sitewise.gate import format_overlay_failure, overlay_status


def test_taxonomy_class_and_work_type_satisfy_gate() -> None:
    status = overlay_status(
        archetype=None,
        state="NSW",
        building_class="residential",
        work_type="refurb",
    )
    assert status.ready
    assert status.issues == []


def test_legacy_archetype_only_still_satisfies_gate() -> None:
    status = overlay_status(
        archetype="small-commercial",
        state="NSW",
    )
    assert status.ready
    assert status.issues == []


def test_neither_taxonomy_nor_archetype_reports_class_and_work_type_missing() -> None:
    status = overlay_status(
        archetype=None,
        state="NSW",
    )
    assert not status.ready
    missing_fields = {issue.field for issue in status.missing}
    assert missing_fields == {"building_class", "work_type"}
    assert all(issue.reason == "missing" for issue in status.missing)


def test_class_set_but_work_type_missing_reports_only_work_type() -> None:
    status = overlay_status(
        archetype=None,
        state="NSW",
        building_class="residential",
        work_type=None,
    )
    assert not status.ready
    assert [issue.field for issue in status.missing] == ["work_type"]


def test_unsupported_archetype_without_taxonomy_reports_taxonomy_missing() -> None:
    status = overlay_status(
        archetype="unsupported",
        state="NSW",
    )
    assert not status.ready
    missing_fields = {issue.field for issue in status.missing}
    assert missing_fields == {"building_class", "work_type"}


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        ("Mars", "unsupported"),
        (None, "missing"),
    ],
)
def test_state_check_unchanged(
    state: str | None,
    reason: str,
) -> None:
    status = overlay_status(
        archetype=None,
        state=state,
        building_class="residential",
        work_type="refurb",
    )
    assert not status.ready
    issue = next(issue for issue in status.issues if issue.field == "state")
    assert issue.reason == reason


def test_role_is_no_longer_gated() -> None:
    # Role is pinned server-side and never blocks the overlay gate.
    status = overlay_status(
        archetype=None,
        state="NSW",
        building_class="residential",
        work_type="refurb",
    )
    assert status.ready
    assert status.issues == []


def test_format_overlay_failure_names_missing_taxonomy() -> None:
    status = overlay_status(
        archetype=None,
        state="NSW",
    )
    message = format_overlay_failure(status)
    assert "building class is missing" in message
    assert "work type is missing" in message
