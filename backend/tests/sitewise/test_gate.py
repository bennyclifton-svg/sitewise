import pytest

from app.sitewise.gate import format_overlay_failure, overlay_status


def test_taxonomy_class_and_work_type_satisfy_gate() -> None:
    status = overlay_status(
        archetype=None,
        user_role="architect-pm",
        state="NSW",
        building_class="residential",
        work_type="refurb",
    )
    assert status.ready
    assert status.issues == []


def test_legacy_archetype_only_still_satisfies_gate() -> None:
    status = overlay_status(
        archetype="small-commercial",
        user_role="architect-pm",
        state="NSW",
    )
    assert status.ready
    assert status.issues == []


def test_neither_taxonomy_nor_archetype_reports_class_and_work_type_missing() -> None:
    status = overlay_status(
        archetype=None,
        user_role="architect-pm",
        state="NSW",
    )
    assert not status.ready
    missing_fields = {issue.field for issue in status.missing}
    assert missing_fields == {"building_class", "work_type"}
    assert all(issue.reason == "missing" for issue in status.missing)


def test_class_set_but_work_type_missing_reports_only_work_type() -> None:
    status = overlay_status(
        archetype=None,
        user_role="architect-pm",
        state="NSW",
        building_class="residential",
        work_type=None,
    )
    assert not status.ready
    assert [issue.field for issue in status.missing] == ["work_type"]


def test_unsupported_archetype_without_taxonomy_reports_taxonomy_missing() -> None:
    status = overlay_status(
        archetype="unsupported",
        user_role="architect-pm",
        state="NSW",
    )
    assert not status.ready
    missing_fields = {issue.field for issue in status.missing}
    assert missing_fields == {"building_class", "work_type"}


@pytest.mark.parametrize(
    ("user_role", "state", "field", "reason"),
    [
        ("TBC", "NSW", "user_role", "tbc"),
        (None, "NSW", "user_role", "missing"),
        ("architect-pm", "Mars", "state", "unsupported"),
        ("architect-pm", None, "state", "missing"),
    ],
)
def test_role_and_state_checks_unchanged(
    user_role: str | None,
    state: str | None,
    field: str,
    reason: str,
) -> None:
    status = overlay_status(
        archetype=None,
        user_role=user_role,
        state=state,
        building_class="residential",
        work_type="refurb",
    )
    assert not status.ready
    issue = next(issue for issue in status.issues if issue.field == field)
    assert issue.reason == reason


def test_format_overlay_failure_names_missing_taxonomy() -> None:
    status = overlay_status(
        archetype=None,
        user_role="architect-pm",
        state="NSW",
    )
    message = format_overlay_failure(status)
    assert "building class is missing" in message
    assert "work type is missing" in message
