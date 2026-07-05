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


def _taxonomy_satisfied(
    *,
    archetype: str | None,
    building_class: str | None,
    work_type: str | None,
) -> bool:
    """The "what kind of project" overlay is ready when the PMP 2.0 taxonomy
    (class + work type) is set, or a supported legacy ``archetype`` is present.

    Taxonomy is authoritative; ``archetype`` is a compatibility fallback for
    old/seeded projects that predate the class/work-type picker.
    """
    if _clean(building_class) is not None and _clean(work_type) is not None:
        return True
    return _clean(archetype) in SUPPORTED_ARCHETYPES


def overlay_status(
    *,
    archetype: str | None,
    user_role: str | None,
    state: str | None,
    building_class: str | None = None,
    work_type: str | None = None,
) -> OverlayStatus:
    missing: list[OverlayIssue] = []
    invalid: list[OverlayIssue] = []

    if not _taxonomy_satisfied(
        archetype=archetype,
        building_class=building_class,
        work_type=work_type,
    ):
        # Report on the taxonomy dropdowns the user can actually set, not the
        # retired ``archetype`` bucket. Flag whichever half is unset.
        for field, value in (("building_class", building_class), ("work_type", work_type)):
            if _clean(value) is None:
                missing.append(OverlayIssue(field=field, value=value, reason="missing"))

    for field, value, supported in (
        ("user_role", user_role, SUPPORTED_USER_ROLES),
        ("state", state, SUPPORTED_STATES),
    ):
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
