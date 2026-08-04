from __future__ import annotations

from app.schemas.project_snapshot import ProjectSnapshot
from app.schemas.workflow_capabilities import (
    WorkflowCapability,
    WorkflowCapabilityMatrix,
)
from app.sitewise.cost_plan_coverage import (
    resolve_cost_plan_coverage,
    unsupported_coverage_reason,
)

CREATE_PMP = "create_pmp"
UPDATE_PMP = "update_pmp"
CREATE_COST_PLAN = "create_cost_plan"
REFRESH_COST_PLAN = "refresh_cost_plan"
EDIT_COST_PLAN = "edit_cost_plan"
APPROVED_TENDER_HANDOFF = "approved_tender_cost_handoff"
TENDER_COMPARISON = "tender_comparison"
CONSULTANT_PROCUREMENT = "consultant_procurement"
CONTRACTOR_EOI = "contractor_eoi"
TRADE_PROCUREMENT = "trade_procurement"
TRANSMITTAL = "transmittal"

_PROJECT_PLAN_FIELDS = ("building_class", "work_type", "state")
_COST_PLAN_FIELDS = ("building_class", "subclasses", "work_type", "state")
_TENDER_FIELDS = ("building_class", "subclasses", "work_type", "state")
_CONSULTANT_FIELDS = ("building_class", "work_type")
_CONTRACTOR_FIELDS = ("building_class", "work_type", "state")
_TENDER_STATES = frozenset({"NSW", "VIC", "QLD"})
_TENDER_WORK_TYPES = frozenset({"new", "refurb", "extend"})
_TENDER_CLASS_1A_SUBCLASSES = frozenset({"house", "townhouses"})
def workflow_capabilities(snapshot: ProjectSnapshot) -> WorkflowCapabilityMatrix:
    """Return the single deterministic capability truth for a project snapshot."""
    plan = _required_profile_capability(snapshot, _PROJECT_PLAN_FIELDS)
    capabilities = {
        CREATE_PMP: plan,
        UPDATE_PMP: plan.model_copy(deep=True),
        CREATE_COST_PLAN: _cost_plan_capability(snapshot, action="create"),
        REFRESH_COST_PLAN: _cost_plan_capability(snapshot, action="refresh"),
        EDIT_COST_PLAN: _cost_plan_capability(snapshot, action="row_edit"),
        APPROVED_TENDER_HANDOFF: _cost_plan_capability(
            snapshot, action="tender_handoff"
        ),
        TENDER_COMPARISON: _tender_capability(snapshot),
        CONSULTANT_PROCUREMENT: _required_profile_capability(
            snapshot,
            _CONSULTANT_FIELDS,
        ),
        CONTRACTOR_EOI: _required_profile_capability(
            snapshot,
            _CONTRACTOR_FIELDS,
        ),
        TRADE_PROCUREMENT: _required_profile_capability(
            snapshot,
            _CONTRACTOR_FIELDS,
        ),
        TRANSMITTAL: WorkflowCapability(
            status="supported",
            reasons=[
                "A transmittal can be drafted from the files selected in the "
                "current document register. It remains unissued until the "
                "recipient and issue details are confirmed."
            ],
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
        reasons=[
            "The required project profile is complete; the workflow will use "
            "available project evidence and applicable platform guidance."
        ],
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
    subclasses = {_subclass_value(item) for item in getattr(profile, "subclasses", [])}
    reasons: list[str] = []
    if profile.building_class != "residential" or not subclasses.issubset(
        _TENDER_CLASS_1A_SUBCLASSES
    ):
        reasons.append(
            "Tender Comparison supports Class 1a houses and townhouses only."
        )
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
        reasons=[
            "The confirmed profile is within Tender Comparison's Class 1a coverage."
        ],
    )


def _cost_plan_capability(
    snapshot: ProjectSnapshot, *, action: str
) -> WorkflowCapability:
    missing = _missing_profile_fields(snapshot, _COST_PLAN_FIELDS)
    if missing:
        return WorkflowCapability(
            status="needs_input",
            reasons=["Cost Plan requires confirmed project context."],
            required_fields=missing,
        )

    profile = snapshot.profile
    confirmations = {
        "create": ["confirm_reference_coverage"],
        "refresh": ["expected_base_version", "confirm_refresh_proposal"],
        "row_edit": ["expected_base_version"],
        "tender_handoff": [
            "approved_frozen_qs_passed_tender",
            "selected_quote_and_package",
            "confirm_apply_as_proposal",
        ],
    }[action]

    if profile.state != "NSW":
        return WorkflowCapability(
            status="unsupported",
            reasons=["Cost Plan reference-data coverage is currently NSW only."],
        )
    if profile.work_type == "remediation" and not profile.work_scope:
        return WorkflowCapability(
            status="needs_input",
            reasons=[
                "Cost Plan remediation coverage depends on the confirmed remediation "
                "scope."
            ],
            required_fields=["work_scope"],
        )

    coverage = resolve_cost_plan_coverage(
        building_class=profile.building_class,
        work_type=profile.work_type,
        subclasses=_profile_subclasses(snapshot),
        work_scopes=_profile_work_scopes(snapshot),
    )
    if coverage is None:
        return WorkflowCapability(
            status="unsupported",
            reasons=[
                unsupported_coverage_reason(
                    building_class=profile.building_class,
                    work_type=profile.work_type,
                )
            ],
        )
    coverage_kind = (
        "structure-only scaffold" if coverage.structure_only else "reference set"
    )
    return WorkflowCapability(
        status="supported",
        reasons=[
            f"The confirmed profile is within the {coverage.label}. The "
            f"{coverage_kind} must be combined with active-project evidence; "
            "missing prices remain TBC and are never filled from general model "
            "knowledge."
        ],
        required_confirmations=confirmations,
        reference_coverage=[coverage.label],
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


def _profile_subclasses(snapshot: ProjectSnapshot) -> set[str]:
    return {
        _subclass_value(item) for item in getattr(snapshot.profile, "subclasses", [])
    }


def _profile_work_scopes(snapshot: ProjectSnapshot) -> set[str]:
    return {
        str(item)
        for item in getattr(snapshot.profile, "work_scope", [])
        if str(item).strip()
    }
