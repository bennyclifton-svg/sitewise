from pydantic import BaseModel, Field

SUPPORTED_ARCHETYPES = {
    "new-dwelling",
    "renovation",
    "multi-dwelling",
    "ancillary",
    "small-commercial",
}
SUPPORTED_USER_ROLES = {"owner-builder", "architect-pm", "builder", "d-and-c"}
SUPPORTED_STATES = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}


class OverlayIssue(BaseModel):
    field: str
    value: str | None
    reason: str


class OverlayStatus(BaseModel):
    ready: bool
    missing: list[OverlayIssue] = Field(default_factory=list)
    invalid: list[OverlayIssue] = Field(default_factory=list)

    @property
    def issues(self) -> list[OverlayIssue]:
        return [*self.missing, *self.invalid]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _is_tbc(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"tbc", "tbd", "to be confirmed"}


def _check_required(
    *,
    field: str,
    value: str | None,
    supported: set[str],
) -> tuple[OverlayIssue | None, OverlayIssue | None]:
    cleaned = _clean(value)
    if cleaned is None:
        return OverlayIssue(field=field, value=value, reason="missing"), None
    if _is_tbc(cleaned):
        return OverlayIssue(field=field, value=value, reason="tbc"), None
    if cleaned not in supported:
        return None, OverlayIssue(field=field, value=value, reason="unsupported")
    return None, None


def overlay_status(
    *,
    archetype: str | None,
    user_role: str | None,
    state: str | None,
) -> OverlayStatus:
    missing: list[OverlayIssue] = []
    invalid: list[OverlayIssue] = []
    checks = [
        ("archetype", archetype, SUPPORTED_ARCHETYPES),
        ("user_role", user_role, SUPPORTED_USER_ROLES),
        ("state", state, SUPPORTED_STATES),
    ]
    for field, value, supported in checks:
        missing_issue, invalid_issue = _check_required(
            field=field,
            value=value,
            supported=supported,
        )
        if missing_issue is not None:
            missing.append(missing_issue)
        if invalid_issue is not None:
            invalid.append(invalid_issue)
    return OverlayStatus(ready=not missing and not invalid, missing=missing, invalid=invalid)


def format_overlay_failure(status: OverlayStatus, *, workflow: str = "Create PMP") -> str:
    if status.ready:
        return "The SiteWise three-overlay gate is satisfied."
    parts = []
    for issue in status.issues:
        label = issue.field.replace("_", " ")
        if issue.reason == "unsupported":
            parts.append(f"{label}={issue.value!r} is unsupported")
        elif issue.reason == "tbc":
            parts.append(f"{label} is TBC")
        else:
            parts.append(f"{label} is missing")
    return f"{workflow} is blocked until these overlays are resolved: " + "; ".join(parts)
