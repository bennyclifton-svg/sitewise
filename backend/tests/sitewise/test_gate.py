import pytest

from app.sitewise.gate import format_overlay_failure, overlay_status


def test_overlay_status_ready_from_taxonomy_alone() -> None:
    status = overlay_status(
        building_class="commercial",
        work_type="new",
        archetype=None,
        user_role="architect-pm",
        state="NSW",
    )
    assert status.ready
    assert status.issues == []


def test_overlay_status_ready_from_legacy_archetype_alone() -> None:
    status = overlay_status(
        building_class=None,
        work_type=None,
        archetype="small-commercial",
        user_role="architect-pm",
        state="NSW",
    )
    assert status.ready
    assert status.issues == []


def test_overlay_status_missing_taxonomy_and_archetype() -> None:
    status = overlay_status(
        building_class=None,
        work_type=None,
        archetype=None,
        user_role="architect-pm",
        state="NSW",
    )
    assert not status.ready
    fields = {issue.field for issue in status.issues}
    assert fields == {"building_class", "work_type"}


def test_overlay_status_class_without_work_type_reports_work_type_missing() -> None:
    status = overlay_status(
        building_class="commercial",
        work_type=None,
        archetype=None,
        user_role="architect-pm",
        state="NSW",
    )
    assert not status.ready
    assert status.issues[0].field == "work_type"
    assert status.issues[0].reason == "missing"


def test_overlay_status_unsupported_archetype_does_not_satisfy_taxonomy_gate() -> None:
    status = overlay_status(
        building_class=None,
        work_type=None,
        archetype="not-a-real-archetype",
        user_role="architect-pm",
        state="NSW",
    )
    assert not status.ready
    fields = {issue.field for issue in status.issues}
    assert fields == {"building_class", "work_type"}


@pytest.mark.parametrize(
    ("user_role", "state", "field", "reason"),
    [
        ("TBC", "NSW", "user_role", "tbc"),
        ("architect-pm", "Mars", "state", "unsupported"),
    ],
)
def test_overlay_status_reports_role_and_state_issues(
    user_role: str | None,
    state: str | None,
    field: str,
    reason: str,
) -> None:
    status = overlay_status(
        building_class="commercial",
        work_type="new",
        archetype=None,
        user_role=user_role,
        state=state,
    )
    assert not status.ready
    assert status.issues[0].field == field
    assert status.issues[0].reason == reason


def test_format_overlay_failure_names_taxonomy_blockers() -> None:
    status = overlay_status(
        building_class=None,
        work_type=None,
        archetype=None,
        user_role="builder",
        state="NSW",
    )
    message = format_overlay_failure(status)
    assert "building class is missing" in message
    assert "work type is missing" in message


def test_overlay_status_default_params_preserve_legacy_call_shape() -> None:
    """Callers that only pass archetype (no taxonomy kwargs) keep working."""
    status = overlay_status(archetype="small-commercial", user_role="builder", state="NSW")
    assert status.ready
