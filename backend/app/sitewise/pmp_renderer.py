"""Deterministic PMP scaffold rendering from a MobilisationEvidencePack."""

from __future__ import annotations

from typing import Literal

from app.database.project import Project
from app.sitewise.mobilisation_evidence import (
    GAP_CERTIFIER,
    GAP_CONSTRUCTION_BUDGET,
    GAP_GEOTECHNICAL,
    GAP_MASTER_PROGRAMME,
    GAP_OWNER_BRIEF,
    MobilisationEvidencePack,
    build_evidence_map_rows,
    build_evidence_on_file_lines,
    has_engagement_evidence,
    has_fee_proposal_evidence,
    pack_has_gap,
)
from app.sitewise.pmp_greenfield_brief import (
    ARCHITECT_PM_PROGRAMME_SUBMILESTONE_TABLE,
    RISK_REGISTER_TABLE,
    _archetype_due_diligence_checklist,
    programme_submilestone_table,
    strip_due_diligence_contract_meta,
)
from app.sitewise.pmp_sources import document_title_for_role, required_section_headings

DraftMode = Literal["evidence_grounded", "platform_seeded"]

NARRATIVE_PLACEHOLDER = "[Pending narrative generation — Phase 3]"

def _baseline_risk_rows(
    pack: MobilisationEvidencePack,
) -> tuple[tuple[str, str, str, str, str], ...]:
    """Baseline risk rows derived from the evidence pack.

    Never names a party or date that is not in the evidence: the DA target is
    read from the pack, and the builder-conflict row stays entity-free and
    reflects whether a conflict was actually disclosed.
    """
    da_target = pack.target_da_lodgement or "DA"
    conflict_status = "Partial" if pack.conflict_disclosure else "Assumption"
    return (
        (
            "Planning pathway / DA programme slip",
            "Owner",
            "Assumption",
            f"Confirm DA pathway and {da_target} lodgement target",
            "TBC",
        ),
        (
            "Reactive soil / footing type unknown",
            "Architect-PM",
            "Assumption",
            "Commission geotechnical report before scheme lock",
            "TBC",
        ),
        (
            "Construction budget not evidenced",
            "Owner",
            "Assumption",
            "Confirm working budget ceiling",
            "TBC",
        ),
        (
            "Builder conflict / related-party tender",
            "Architect-PM",
            conflict_status,
            "Confirm related-party / conflict status of invited builders "
            "before tender list lock",
            "TBC",
        ),
        (
            "Utility / Sydney Water lead times",
            "Owner",
            "Assumption",
            "Obtain sewer diagram and confirm capacity",
            "TBC",
        ),
    )


def _renovation_risk_rows(
    pack: MobilisationEvidencePack,
) -> tuple[tuple[str, str, str, str, str], ...]:
    """Renovation-specific risks grounded in existing-building evidence.

    Replaces greenfield assumptions (reactive soil, footing type) with the
    risks that actually drive a renovation: latent conditions in retained
    fabric, heritage controls, and live occupation. Specialist reports stay
    owner-commissioned per the engagement scope.
    """
    da_target = pack.target_da_lodgement or "DA"
    conflict_status = "Partial" if pack.conflict_disclosure else "Assumption"
    return (
        (
            "Latent conditions in existing footings / masonry tie-ins",
            "Architect-PM",
            "Assumption",
            "Allow contingency / provisional sums; stage investigation before scheme lock",
            "TBC",
        ),
        (
            "Heritage / conservation-area controls",
            "Architect-PM",
            "Assumption",
            f"Confirm controls and heritage impact statement scope; "
            f"DA pathway, {da_target} lodgement target",
            "TBC",
        ),
        (
            "Live occupation — dust, noise and safety controls",
            "Owner",
            "Assumption",
            "Confirm occupation vs decant; price site protection and controls",
            "TBC",
        ),
        (
            "Construction budget not evidenced",
            "Owner",
            "Assumption",
            "Confirm working budget ceiling",
            "TBC",
        ),
        (
            "Specialist reports not on file (geotechnical / survey)",
            "Owner",
            "Assumption",
            "Architect-PM to coordinate owner's appointment of consultants "
            "(owner-commissioned per engagement)",
            "TBC",
        ),
        (
            "Builder conflict / related-party tender",
            "Architect-PM",
            conflict_status,
            "Confirm related-party / conflict status of invited builders "
            "before tender list lock",
            "TBC",
        ),
    )


def _table_lines_from_brief(block: str) -> str:
    lines: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            lines.append(line.rstrip())
        elif lines and not stripped:
            break
    return "\n".join(lines)


def _bullet_lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items if item.strip())


def _labeled_field(label: str, text: str | None) -> str:
    """Render a label/value line without duplicating trailing sentence punctuation."""
    value = (text or "TBC").strip()
    if value.endswith((".", "!", "?")):
        return f"{label}: {value}"
    return f"{label}: {value}."


def _fee_stage_table(pack: MobilisationEvidencePack) -> str:
    rows = ["| Stage | Trigger | Fee (ex GST) |", "| --- | --- | --- |"]
    for stage in pack.fee_stages:
        rows.append(f"| {stage.stage} | {stage.trigger} | {stage.fee_ex_gst} |")
    return "\n".join(rows)


def _render_evidence_basis(
    pack: MobilisationEvidencePack,
    *,
    version: int,
) -> str:
    evidence_lines = build_evidence_on_file_lines(pack) or [
        "Assumption: mobilisation evidence not yet indexed."
    ]
    gap_lines = pack.gaps or ["None identified"]
    map_rows = ["| Section | Evidence status | Ref |", "| --- | --- | --- |"]
    for section, status, ref in build_evidence_map_rows(pack):
        map_rows.append(f"| {section} | {status} | {ref} |")
    evidence_map = "\n".join(map_rows)
    return "\n".join(
        [
            "## Evidence basis and document control",
            "",
            f"Status: draft, review-only, not issued. Version v{version:02d}.",
            "Source hierarchy: project evidence (listed below) → doctrine → seeds.",
            "",
            "**Evidence on file:**",
            _bullet_lines(evidence_lines),
            "",
            "**Gaps:**",
            _bullet_lines(gap_lines),
            "",
            evidence_map,
            "",
            "Document control: save under `00-brief-pmp/`; supersede when new evidence arrives.",
            "Decision register to open under `08-meetings-reporting/` (append-only).",
        ]
    )


def _render_project_overview(project: Project, pack: MobilisationEvidencePack) -> str:
    budget_gap = pack_has_gap(pack, GAP_CONSTRUCTION_BUDGET)
    if budget_gap:
        budget_line = "Assumption: working construction budget not yet evidenced."
    elif pack.construction_budget_ceiling:
        budget_line = (
            f"Construction budget confirmed — {pack.construction_budget_ceiling} working ceiling "
            "(owner project brief)."
        )
    else:
        budget_line = "Construction budget: evidenced — see owner project brief."
    return "\n".join(
        [
            "## Project overview",
            "",
            f"Archetype: {project.archetype or 'TBC'}. Role: {project.user_role or 'architect-pm'}. "
            f"State: {project.state or 'NSW'}.",
            f"Owners: {pack.owners or 'TBC'}.",
            f"Site: {pack.site_address or 'TBC'}.",
            _labeled_field("Dwelling", pack.dwelling_summary),
            _labeled_field("Site constraints", pack.site_constraints),
            (
                f"Mobilisation: post-engagement (engagement executed "
                f"{pack.engagement_executed_date or 'TBC'})."
                if has_engagement_evidence(pack)
                else "Mobilisation: pre-engagement — executed engagement letter not on file."
            ),
            budget_line,
        ]
    )


def _render_role_and_appointment(pack: MobilisationEvidencePack) -> str:
    engaged = has_engagement_evidence(pack)
    if pack.scope_bullets:
        scope_lines = pack.scope_bullets
    elif engaged:
        scope_lines = ["Scope per engagement letter."]
    else:
        scope_lines = [
            "Scope of services not evidenced — obtain and file the executed engagement letter."
        ]
    architect_row = (
        "| Architect / PM (advisory) | Yes | Per executed engagement letter |"
        if engaged
        else "| Architect / PM (advisory) | Declared (project overlay) | "
        "Engagement letter not on file — obtain and file |"
    )
    role_table = "\n".join(
        [
            "| Role | Appointed | Notes |",
            "| --- | --- | --- |",
            architect_row,
            "| Superintendent | No | Not appointed unless separately agreed |",
            "| Certifier | No | Owner to appoint |",
            "| Contract administrator | Per engagement | CA during construction; not Superintendent |",
        ]
    )
    pi_block = (
        f"PI insurance: {pack.pi_holder or pack.appointee or 'Architect-PM'} holds policy "
        f"with {pack.pi_insurer or 'TBC'}, "
        f"ref {pack.pi_policy_ref or 'TBC'}, limit {pack.pi_limit or 'TBC'}, "
        f"period {pack.pi_period or 'TBC'}. Certificate on request."
    )
    builder_checklist = _bullet_lines(
        [
            "Verify builder licence and QS before award.",
            "Verify HBCF/HOW per-project certificate.",
            "Verify LSL receipt before CC (CC-blocking).",
            "Verify executed head contract, CWI, PL, and workers compensation.",
        ]
    )
    return "\n".join(
        [
            "## Architect-PM role and appointment",
            "",
            role_table,
            "",
            f"Appointee: {pack.appointee or 'TBC'}. Roles: {pack.roles or 'TBC'}.",
            (
                f"Engagement executed on file ({pack.engagement_executed_date or 'TBC'})."
                if engaged
                else "Engagement letter not on file — engagement status unverified."
            ),
            "",
            "**Scope of services (engagement letter):**",
            _bullet_lines(scope_lines),
            "",
            pi_block,
            "",
            "**Builder instruments (verify only — not held by architect-PM):**",
            builder_checklist,
        ]
    )


def _render_two_brief_discipline(pack: MobilisationEvidencePack) -> str:
    if pack.owner_brief_on_file and not pack_has_gap(pack, GAP_OWNER_BRIEF):
        signed = (
            f" — **signed {pack.owner_brief_signed_date}**"
            if pack.owner_brief_signed_date
            else " — **signed on file**"
        )
        owner_brief_line = (
            f"**Owner project brief (on file):** scope, budget, and programme aspirations per "
            f"signed owner brief{signed}."
        )
    elif has_fee_proposal_evidence(pack):
        owner_brief_line = (
            "**Owner project brief:** draft from fee proposal project understanding — "
            "**pending owner formal sign-off**."
        )
    else:
        owner_brief_line = (
            "**Owner project brief:** to be drafted with the owner — "
            "**pending owner formal sign-off**."
        )
    if has_engagement_evidence(pack):
        engagement_brief_line = (
            "**Engagement brief (on file):** fee, scope, PMP, governance, reporting, and procurement "
            "services per executed engagement letter and fee proposal."
        )
    else:
        engagement_brief_line = (
            "**Engagement brief:** not evidenced — executed engagement letter and fee proposal "
            "to be obtained and filed."
        )
    return "\n".join(
        [
            "## Two-brief discipline",
            "",
            engagement_brief_line,
            owner_brief_line,
            "Extra tender round = engagement variation; material scope change = owner project brief "
            "+ decision register entry.",
        ]
    )


def _render_governance(pack: MobilisationEvidencePack) -> str:
    raci = "\n".join(
        [
            "| Activity | Owner | Architect-PM | Consultants | Builder | Certifier |",
            "| --- | --- | --- | --- | --- | --- |",
            "| Scope / budget decisions | Decides | Recommends | Advises | Executes | — |",
            "| Planning pathway | Decides | Recommends | Advises | — | Certifies |",
            "| Builder award / contract | Decides | Recommends | — | Executes | — |",
            "| Authority submissions | Approves | Coordinates | Prepares | — | Certifies |",
        ]
    )
    gates = _bullet_lines(
        [
            "Planning pathway confirmed.",
            "Scheme endorsed for DA lodgement.",
            "Builder awarded and head contract executed.",
            "Construction Certificate issued.",
            "Practical completion and OC issued.",
        ]
    )
    return "\n".join(
        [
            "## Governance and decisions",
            "",
            raci,
            "",
            "**Decision gates:**",
            gates,
            "",
            (
                f"Owner approval rule (engagement letter): "
                f"{pack.owner_approval_rule or 'Written approval required.'}"
                if has_engagement_evidence(pack)
                else "Owner approval rule: written approval required for material decisions "
                "(to be confirmed in the engagement letter once on file)."
            ),
            "All decisions append-only under `08-meetings-reporting/`.",
        ]
    )


def _render_communications(pack: MobilisationEvidencePack) -> str:
    return "\n".join(
        [
            "## Communications protocol",
            "",
            f"Owner update cadence: {pack.reporting_cadence or 'Monthly progress reporting'}.",
            "Forums: owner update, consultant coordination, builder RFIs (post-award), "
            "authority/certifier route.",
            "Emergency contact route: architect-PM primary; owner decision on material issues.",
            "",
            "**Owner escalation format (mandatory for material decisions):**",
            "1. What this means for you",
            "2. What we need from you (with due date)",
            "3. What's happened",
            "4. What's next",
            "5. Background (if needed)",
            "",
            "Provide a clear recommendation — not an option bundle without a view.",
        ]
    )


def _render_fee_services(pack: MobilisationEvidencePack) -> str:
    engaged = has_engagement_evidence(pack)
    if pack.service_exclusions:
        exclusions = pack.service_exclusions
    elif engaged:
        exclusions = "Per engagement letter exclusions."
    else:
        exclusions = "Not evidenced — no executed engagement letter on file."
    fee_line = (
        f"Fixed fee {pack.fee_total_ex_gst or 'TBC'} ex GST, staged per engagement letter."
        if engaged
        else "Fixed fee not evidenced — no executed engagement letter on file."
    )
    procurement_notes = _bullet_lines(
        [
            fee_line,
            f"Disbursements: {pack.disbursements or 'TBC'}.",
            f"Invited builders: {pack.invited_builder_count or 'TBC'}; "
            f"formal head-builder tenders: {pack.formal_tender_count or 'TBC'}.",
            f"CA phase assumed {pack.ca_months_assumed or 'TBC'} months.",
            f"Conflict disclosure: {pack.conflict_disclosure or 'None stated.'}",
        ]
    )
    return "\n".join(
        [
            "## Fee, services and programme relationship",
            "",
            _fee_stage_table(pack),
            "",
            "**Service exclusions (engagement letter — distinct from building scope):**",
            exclusions,
            "",
            "**Procurement / fee assumptions:**",
            procurement_notes,
        ]
    )


def _render_scope_change(pack: MobilisationEvidencePack) -> str:
    if pack.owner_brief_on_file and not pack_has_gap(pack, GAP_OWNER_BRIEF):
        scope_prefix = "Building scope (per signed owner project brief)"
    else:
        scope_prefix = "Building scope (draft pending owner brief sign-off)"
    return "\n".join(
        [
            "## Scope and change control",
            "",
            _labeled_field(scope_prefix, pack.dwelling_summary),
            _labeled_field("Site / planning constraints", pack.site_constraints),
            "Service exclusions: "
            + (
                pack.service_exclusions
                or (
                    "Per engagement letter."
                    if has_engagement_evidence(pack)
                    else "Not evidenced — no executed engagement letter on file."
                )
            ),
            "Project-scope change = owner decision + brief update; service-scope change = engagement variation.",
        ]
    )


def _render_approvals(project: Project, pack: MobilisationEvidencePack) -> str:
    archetype = project.archetype or "new-dwelling"
    state = project.state or "NSW"
    due_diligence = strip_due_diligence_contract_meta(
        _archetype_due_diligence_checklist(archetype, state=state)
    )
    authority_table = _nsw_authority_tracker_table(state, pack)
    return "\n".join(
        [
            "## Approvals and compliance",
            "",
            due_diligence,
            "",
            f"Planning pathway (fee proposal): {pack.planning_pathway or 'TBC — confirm CDC vs DA.'}",
            "",
            "### Authority tracker",
            authority_table,
            "",
            "File due diligence under `03-design/01-due-diligence/`; "
            "authority tracker under `00-brief-pmp/` or `04-authority/`.",
        ]
    )


def _nsw_authority_tracker_table(state: str, pack: MobilisationEvidencePack) -> str:
    da_status = "Partial" if pack.target_da_lodgement else "Assumption"
    da_action = (
        f"Target lodgement {pack.target_da_lodgement}"
        if pack.target_da_lodgement
        else "Confirm pathway"
    )
    rows = [
        "| Authority / instrument | Status | Responsible party | Next action |",
        "| --- | --- | --- | --- |",
    ]
    if state == "NSW":
        rows.append(
            "| BASIX (commitment) | Assumption | Owner / Architect-PM | Appoint assessor; align with DA |"
        )
    certifier_status = (
        "Partial"
        if not pack_has_gap(pack, GAP_CERTIFIER)
        else "Assumption"
    )
    certifier_action = (
        "Appointed — coordinate CC pathway"
        if not pack_has_gap(pack, GAP_CERTIFIER)
        else "Appoint before CC"
    )
    rows.extend(
        [
            f"| Principal certifier | {certifier_status} | Owner | {certifier_action} |",
            f"| DA / planning permit | {da_status} | Owner / Architect-PM | {da_action} |",
            "| Construction Certificate | Assumption | Certifier | Issue before site start |",
            "| LSL receipt | Assumption | Builder | CC-blocking prerequisite |",
            f"| Utility connections ({state}) | Assumption | Owner / builder | Confirm capacity |",
            "| Occupation Certificate | Assumption | Certifier | Issue at handover |",
        ]
    )
    return "\n".join(rows)


def _render_programme(pack: MobilisationEvidencePack, user_role: str) -> str:
    submilestone_block = programme_submilestone_table(user_role)
    submilestone_table = _table_lines_from_brief(submilestone_block) or _table_lines_from_brief(
        ARCHITECT_PM_PROGRAMME_SUBMILESTONE_TABLE
    )
    brief_note = (
        "brief signed on file"
        if pack.owner_brief_on_file and not pack_has_gap(pack, GAP_OWNER_BRIEF)
        else "subject to due diligence and brief sign-off"
    )
    target_line = (
        f"Target DA lodgement: **{pack.target_da_lodgement}** (engagement letter); {brief_note}."
        if pack.target_da_lodgement
        else "Target DA lodgement: Assumption — confirm with owner."
    )
    programme_note = (
        "Master programme on file — activity durations per programme v0.1."
        if not pack_has_gap(pack, GAP_MASTER_PROGRAMME)
        else "Assumption: activity durations TBC unless evidenced in master programme."
    )
    return "\n".join(
        [
            "## Programme and staging regime",
            "",
            "Baseline 3-stage regime:",
            "- Stage 1: concept/schematic through DA/CDC lodgement and determination.",
            "- Stage 2: design development.",
            "- Stage 3: construction documentation, procurement, and delivery.",
            "",
            target_line,
            "",
            "### Sub-milestone table",
            submilestone_table,
            "",
            programme_note,
        ]
    )


def _render_cost_procurement(pack: MobilisationEvidencePack) -> str:
    if pack_has_gap(pack, GAP_CONSTRUCTION_BUDGET):
        if pack.builder_quotes:
            budget_line = (
                "Assumption: construction budget not evidenced — owner to confirm working "
                "budget ceiling. Unverified builder pricing is on file (below) as a market "
                "signal only; it is not an owner budget."
            )
        else:
            budget_line = (
                "Assumption: construction budget not evidenced — owner to confirm working budget ceiling."
            )
    elif pack.construction_budget_ceiling:
        budget_line = (
            f"Construction budget confirmed — {pack.construction_budget_ceiling} working ceiling "
            "(owner project brief)."
        )
    else:
        budget_line = "Construction budget confirmed per owner project brief."
    quote_block: list[str] = []
    if pack.builder_quotes:
        quote_block = ["", "**Builder pricing on file (unverified):**", _bullet_lines(pack.builder_quotes)]
    missing = ["elemental cost plan", "tender evaluation matrix"]
    if pack_has_gap(pack, GAP_MASTER_PROGRAMME):
        missing.insert(1, "master programme")
    missing_line = f"Missing artefacts: {', '.join(missing)}."
    return "\n".join(
        [
            "## Cost, programme and procurement posture",
            "",
            "HIA elemental / residential cost plan posture: contingency 5–10%; PC sums and "
            "owner-supplied items tracked separately.",
            budget_line,
            *quote_block,
            "",
            "**Head-builder procurement:**",
            _bullet_lines(
                [
                    f"{pack.invited_builder_count or '2–3'} invited builders; "
                    f"{pack.formal_tender_count or '1'} formal head-builder tender assumed.",
                    f"Conflict disclosure before tender list lock: {pack.conflict_disclosure or 'None stated.'}",
                    "Evaluation criteria to be agreed before tender close.",
                    "Tender evaluation matrix under `05-procurement/`.",
                    "Single clear recommendation to owner with conflict disclosure where applicable.",
                ]
            ),
            "",
            missing_line,
        ]
    )


def _render_consultant_coordination(pack: MobilisationEvidencePack) -> str:
    geotech_status = (
        "Report on file"
        if not pack_has_gap(pack, GAP_GEOTECHNICAL)
        else "Report not on file"
    )
    geotech_appointed = "Yes" if not pack_has_gap(pack, GAP_GEOTECHNICAL) else "No"
    certifier_appointed = "Yes" if not pack_has_gap(pack, GAP_CERTIFIER) else "No"
    certifier_status = (
        "Appointed"
        if not pack_has_gap(pack, GAP_CERTIFIER)
        else "Assumption"
    )
    certifier_notes = (
        "Principal certifier appointed"
        if not pack_has_gap(pack, GAP_CERTIFIER)
        else "Not yet appointed"
    )
    tracker = "\n".join(
        [
            "| Discipline | Appointed | Status | Notes |",
            "| --- | --- | --- | --- |",
            (
                f"| Architect / PM ({pack.appointee or 'Architect-PM'}) | Yes | Executed "
                f"{pack.engagement_executed_date or 'TBC'} | Engagement letter on file |"
                if has_engagement_evidence(pack)
                else f"| Architect / PM ({pack.appointee or 'Architect-PM'}) | Declared | "
                "Assumption | Engagement letter not on file |"
            ),
            "| Structural engineer | No | Assumption | Not yet appointed |",
            "| Hydraulic / BASIX | No | Assumption | Not yet appointed |",
            "| Surveyor | No | Assumption | Not yet appointed |",
            f"| Geotechnical | {geotech_appointed} | "
            f"{'Grounded' if not pack_has_gap(pack, GAP_GEOTECHNICAL) else 'Assumption'} | "
            f"{geotech_status} |",
            f"| Principal certifier | {certifier_appointed} | {certifier_status} | {certifier_notes} |",
        ]
    )
    return "\n".join(
        [
            "## Consultant coordination",
            "",
            tracker,
            "",
            "Responsibility matrix and advice register to open under `02-consultant/`.",
            "Map consultant fee stages to PMP programme stages.",
        ]
    )


def _render_risks_skeleton(project: Project, pack: MobilisationEvidencePack) -> str:
    risk_header = _table_lines_from_brief(RISK_REGISTER_TABLE).splitlines()[0:2]
    rows = list(risk_header)
    if project.archetype == "renovation":
        risk_rows = _renovation_risk_rows(pack)
    else:
        risk_rows = _baseline_risk_rows(pack)
    for risk, owner, status, action, due in risk_rows:
        if pack_has_gap(pack, GAP_CONSTRUCTION_BUDGET) is False and "budget not evidenced" in risk.lower():
            continue
        rows.append(f"| {risk} | {owner} | {status} | {action} | {due} |")
    return "\n".join(
        [
            "## Risks, decisions and next actions",
            "",
            "\n".join(rows),
            "",
            "Registers to open: action, decision, risk, authority approvals, consultant appointment.",
            f"Risk wording and owner decision due dates: {NARRATIVE_PLACEHOLDER}",
        ]
    )


def _prioritized_internal_audit_facts(pack: MobilisationEvidencePack) -> list[str]:
    """Facts for internal audit — brief and budget precede fee/pathway when evidenced."""
    engaged = has_engagement_evidence(pack)
    holder = pack.pi_holder or "Architect-PM"
    facts: list[str] = [
        (
            f"{holder} engaged as architect-PM; engagement executed "
            f"{pack.engagement_executed_date or 'TBC'}."
            if engaged
            else "Architect-PM role declared on the project record; executed engagement "
            "letter not on file."
        ),
    ]
    if pack.owner_brief_on_file and not pack_has_gap(pack, GAP_OWNER_BRIEF):
        signed = pack.owner_brief_signed_date or "on file"
        facts.append(f"Owner project brief signed {signed}.")
    if pack.construction_budget_ceiling and not pack_has_gap(pack, GAP_CONSTRUCTION_BUDGET):
        facts.append(
            f"Construction budget confirmed {pack.construction_budget_ceiling} working ceiling."
        )
    for quote in pack.builder_quotes:
        facts.append(quote)
    if engaged:
        facts.append(
            f"Fixed fee {pack.fee_total_ex_gst or 'TBC'} ex GST on staged triggers "
            "per engagement letter."
        )
    facts.append(f"DA pathway: {pack.planning_pathway or 'TBC'}.")
    if pack.target_da_lodgement:
        facts.append(f"Target DA lodgement {pack.target_da_lodgement} per engagement letter.")
    return facts[:5]


def _render_internal_audit(pack: MobilisationEvidencePack) -> str:
    facts = _prioritized_internal_audit_facts(pack)
    assumptions = [f"Assumption: {gap}." for gap in pack.gaps] or ["Assumption: none identified."]
    workflow_warnings = [
        f"Workflow warning: {gap}."
        for gap in pack.gaps
        if gap not in (GAP_OWNER_BRIEF, GAP_CONSTRUCTION_BUDGET)
    ]
    warning_lines = (
        [f"  - {item}" for item in workflow_warnings]
        if workflow_warnings
        else [f"  - {NARRATIVE_PLACEHOLDER}"]
    )
    return "\n".join(
        [
            "## Internal audit layer",
            "",
            "- **Facts**",
            *[f"  - {fact}" for fact in facts],
            "- **Assumptions**",
            *[f"  - {item}" for item in assumptions],
            "- **Judgements**",
            f"  - {NARRATIVE_PLACEHOLDER}",
            "- **Recommendations**",
            f"  - {NARRATIVE_PLACEHOLDER}",
            "- **Register rows**",
            f"  - {NARRATIVE_PLACEHOLDER}",
            "- **Workflow warnings**",
            *warning_lines,
        ]
    )


def render_pmp_scaffold(
    project: Project,
    pack: MobilisationEvidencePack,
    draft_mode: DraftMode,
    *,
    version: int = 1,
) -> str:
    """Render deterministic PMP markdown scaffold from project overlays and evidence pack."""
    if draft_mode != "evidence_grounded":
        msg = f"PMP scaffold renderer supports evidence_grounded mode only (got {draft_mode!r})"
        raise ValueError(msg)

    user_role = project.user_role or "architect-pm"
    if user_role != "architect-pm":
        msg = f"PMP scaffold renderer supports architect-pm role only (got {user_role!r})"
        raise ValueError(msg)

    sections = [
        _render_evidence_basis(pack, version=version),
        _render_project_overview(project, pack),
        _render_role_and_appointment(pack),
        _render_two_brief_discipline(pack),
        _render_governance(pack),
        _render_communications(pack),
        _render_fee_services(pack),
        _render_scope_change(pack),
        _render_approvals(project, pack),
        _render_programme(pack, user_role),
        _render_cost_procurement(pack),
        _render_consultant_coordination(pack),
        _render_risks_skeleton(project, pack),
        _render_internal_audit(pack),
    ]

    headings = required_section_headings(user_role)
    rendered_headings = {
        line.strip()[3:].strip().lower()
        for section in sections
        for line in section.splitlines()
        if line.strip().startswith("## ")
    }
    missing = [heading for heading in headings if heading.lower() not in rendered_headings]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"PMP scaffold missing required sections: {joined}")

    title = document_title_for_role(user_role)
    body = "\n\n".join(sections)
    return f"# {title}\n\n{body}\n"
