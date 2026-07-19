from __future__ import annotations

from app.schemas.project_snapshot import ProjectSnapshot
from app.schemas.workflow_capabilities import (
    WorkflowCapability,
    WorkflowCapabilityMatrix,
)

CREATE_PMP = "create_pmp"
UPDATE_PMP = "update_pmp"
CREATE_COST_PLAN = "create_cost_plan"
TENDER_COMPARISON = "tender_comparison"
CONSULTANT_PROCUREMENT = "consultant_procurement"

_PROJECT_PLAN_FIELDS = ("building_class", "work_type", "user_role", "state")
_TENDER_FIELDS = ("building_class", "subclasses", "work_type", "state")
_CONSULTANT_FIELDS = ("building_class", "work_type", "user_role")
_TENDER_STATES = frozenset({"NSW", "VIC", "QLD"})
_TENDER_WORK_TYPES = frozenset({"new", "refurb", "extend"})
_TENDER_CLASS_1A_SUBCLASSES = frozenset({"house", "townhouses"})


def workflow_capabilities(snapshot: ProjectSnapshot) -> WorkflowCapabilityMatrix:
    """Return the single deterministic capability truth for a project snapshot."""
    plan = _required_profile_capability(snapshot, _PROJECT_PLAN_FIELDS)
    capabilities = {
        CREATE_PMP: plan,
        UPDATE_PMP: plan.model_copy(deep=True),
        CREATE_COST_PLAN: _cost_plan_capability(snapshot),
        TENDER_COMPARISON: _tender_capability(snapshot),
        CONSULTANT_PROCUREMENT: _required_profile_capability(
            snapshot,
            _CONSULTANT_FIELDS,
        ),
    }
    return WorkflowCapabilityMatrix(
        snapshot_content_fingerprint=snapshot.content_fingerprint,
        capabilities=capabilities,
    )


def capability_for(
    snapshot: ProjectSnapshot,
    workflow: str,
) -> WorkflowCapability:
    matrix = workflow_capabilities(snapshot)
    try:
        return matrix.capabilities[workflow]
    except KeyError as exc:
        raise ValueError(f"Unknown workflow capability: {workflow!r}") from exc


def capability_block_message(snapshot: ProjectSnapshot, workflow: str) -> str | None:
    capability = capability_for(snapshot, workflow)
    if capability.status == "supported":
        return None
    details = "; ".join(capability.reasons)
    if capability.required_fields:
        details += f" Required fields: {', '.join(capability.required_fields)}."
    return f"Workflow capability is {capability.status}: {details}"


def _required_profile_capability(
    snapshot: ProjectSnapshot,
    fields: tuple[str, ...],
) -> WorkflowCapability:
    missing = _missing_profile_fields(snapshot, fields)
    if missing:
        return WorkflowCapability(
            status="needs_input",
            reasons=["Complete the required project profile fields."],
            required_fields=missing,
        )
    return WorkflowCapability(
        status="supported",
        reasons=["The confirmed project profile is within this workflow's coverage."],
    )


def _tender_capability(snapshot: ProjectSnapshot) -> WorkflowCapability:
    missing = _missing_profile_fields(snapshot, _TENDER_FIELDS)
    if missing:
        return WorkflowCapability(
            status="needs_input",
            reasons=["Tender Comparison requires confirmed Class 1a project context."],
            required_fields=missing,
        )

    profile = snapshot.profile
    subclasses = {
        _subclass_value(item) for item in getattr(profile, "subclasses", [])
    }
    reasons: list[str] = []
    if profile.building_class != "residential" or not subclasses.issubset(
        _TENDER_CLASS_1A_SUBCLASSES
    ):
        reasons.append("Tender Comparison supports Class 1a houses and townhouses only.")
    if profile.state not in _TENDER_STATES:
        reasons.append("Tender Comparison supports projects in NSW, VIC, or QLD only.")
    if profile.work_type not in _TENDER_WORK_TYPES:
        reasons.append(
            "Tender Comparison supports new builds, refurbishments, and extensions only."
        )
    if reasons:
        return WorkflowCapability(status="unsupported", reasons=reasons)
    return WorkflowCapability(
        status="supported",
        reasons=["The confirmed profile is within Tender Comparison's Class 1a coverage."],
    )


def _cost_plan_capability(snapshot: ProjectSnapshot) -> WorkflowCapability:
    missing = _missing_profile_fields(snapshot, _PROJECT_PLAN_FIELDS)
    if missing:
        return WorkflowCapability(
            status="needs_input",
            reasons=["Cost Plan requires confirmed project and role context."],
            required_fields=missing,
        )

    profile = snapshot.profile
    reasons: list[str] = []
    if profile.building_class != "residential":
        reasons.append("Cost Plan reference-data coverage is currently residential only.")
    if profile.state != "NSW":
        reasons.append("Cost Plan reference-data coverage is currently NSW only.")
    if profile.user_role != "architect-pm":
        reasons.append("Cost Plan rendering currently supports the architect-PM role only.")
    if reasons:
        return WorkflowCapability(status="unsupported", reasons=reasons)
    return WorkflowCapability(
        status="supported",
        reasons=["The confirmed profile is within current NSW residential Cost Plan coverage."],
    )


def _missing_profile_fields(
    snapshot: ProjectSnapshot,
    fields: tuple[str, ...],
) -> list[str]:
    profile = snapshot.profile
    missing: list[str] = []
    for field in fields:
        value = getattr(profile, field, None)
        if value is None or value == "" or value == []:
            missing.append(field)
    return missing


def _subclass_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return str(getattr(value, "value", ""))
