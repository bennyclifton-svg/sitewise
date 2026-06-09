import pytest

from app.sitewise.gate import format_overlay_failure, overlay_status


def test_overlay_status_passes_for_supported_values() -> None:
    status = overlay_status(
        archetype="small-commercial",
        user_role="architect-pm",
        state="NSW",
    )
    assert status.ready
    assert status.issues == []


@pytest.mark.parametrize(
    ("archetype", "user_role", "state", "field", "reason"),
    [
        (None, "architect-pm", "NSW", "archetype", "missing"),
        ("", "architect-pm", "NSW", "archetype", "missing"),
        ("TBC", "architect-pm", "NSW", "archetype", "tbc"),
        ("unsupported", "architect-pm", "NSW", "archetype", "unsupported"),
        ("small-commercial", "TBC", "NSW", "user_role", "tbc"),
        ("small-commercial", "architect-pm", "Mars", "state", "unsupported"),
    ],
)
def test_overlay_status_reports_specific_issue(
    archetype: str | None,
    user_role: str | None,
    state: str | None,
    field: str,
    reason: str,
) -> None:
    status = overlay_status(archetype=archetype, user_role=user_role, state=state)
    assert not status.ready
    assert status.issues[0].field == field
    assert status.issues[0].reason == reason


def test_format_overlay_failure_names_blockers() -> None:
    status = overlay_status(archetype="TBC", user_role="builder", state="NSW")
    assert "archetype is TBC" in format_overlay_failure(status)
