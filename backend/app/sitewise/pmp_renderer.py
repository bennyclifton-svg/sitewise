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
from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context, project_has_taxonomy
from app.sitewise.section_contracts import heading_for_section_id, pmp_section_headings
from app.sitewise.taxonomy import work_scope_items_for

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


_RISK_SEVERITY_RANK: dict[str, int] = {
    "critical": 0,
    "warning": 1,
    "info": 2,
}


def _ranked_risk_rows(
    rows: list[tuple[str, str, str, str, str, str | None]],
) -> list[tuple[str, str, str, str, str]]:
    ranked = sorted(
        rows,
        key=lambda row: (_RISK_SEVERITY_RANK.get(row[5] or "info", 3), row[0]),
    )
    return [row[:5] for row in ranked[:8]]


def _taxonomy_risk_rows(
    project: Project,
    pack: MobilisationEvidencePack | None = None,
) -> tuple[tuple[str, str, str, str, str], ...]:
    context = pmp_taxonomy_context(project)
    if context is None:
        return ()

    if pack is not None:
        if project.archetype == "renovation":
            base = _renovation_risk_rows(pack)
        else:
            base = _baseline_risk_rows(pack)
    else:
        base = (
            (
                "Project setup incomplete",
                "Owner",
                "Assumption",
                "Confirm scope, budget, approvals pathway, and decision owner",
                "TBC",
            ),
            (
                "Current corpus evidence not uploaded",
                "Architect-PM",
                "Not evidenced",
                "Upload brief, authority, cost, programme, and consultant records",
                "TBC",
            ),
            (
                "Consultant and approval pathway unresolved",
                "Architect-PM",
                "Assumption",
                "Confirm discipline roster and approval certifier/authority path",
                "TBC",
            ),
        )

    rows: list[tuple[str, str, str, str, str, str | None]] = [
        (*row, "warning") for row in base
    ]
    rows.extend(
        (
            flag.title,
            "Architect-PM",
            "Assumption",
            flag.description,
            "TBC",
            flag.severity,
        )
        for flag in context.risk_flags
    )
    return tuple(_ranked_risk_rows(rows))


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
    heritage_status = "Partial" if pack.heritage_advice else "Assumption"
    heritage_action = (
        "Prepare HIS at schematic stage; retain/repair front facade and roof form; "
        f"allow approval timing in {da_target} programme"
        if pack.heritage_advice
        else f"Confirm controls and heritage impact statement scope; DA pathway, "
        f"{da_target} lodgement target"
    )
    live_signal = " ".join([pack.dwelling_summary or "", *pack.builder_rom_caveats])
    live_status = "Partial" if "live occupation" in live_signal.lower() else "Assumption"
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
            heritage_status,
            heritage_action,
            "TBC",
        ),
        (
            "Live occupation — dust, noise and safety controls",
            "Owner",
            live_status,
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


def _optional_bullet_block(label: str, items: list[str]) -> list[str]:
    if not items:
        return []
    return ["", f"**{label}:**", _bullet_lines(items)]


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
            *_optional_bullet_block("Owner design objectives", pack.owner_brief_objectives),
            *_optional_bullet_block("Heritage design constraints", pack.heritage_design_advice),
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


def _render_heritage_controls(pack: MobilisationEvidencePack) -> str:
    if not (pack.heritage_context or pack.heritage_approval_advice or pack.heritage_design_advice):
        return ""
    lines = ["### Heritage / character controls"]
    if pack.heritage_context:
        lines.append(_labeled_field("Status", pack.heritage_context))
    if pack.heritage_approval_advice:
        lines.append(_labeled_field("Approval advice", pack.heritage_approval_advice))
    if pack.heritage_design_advice:
        lines.extend(["", "**Design controls:**", _bullet_lines(pack.heritage_design_advice)])
    return "\n".join(lines)


def _render_approvals(project: Project, pack: MobilisationEvidencePack) -> str:
    archetype = project.archetype or "new-dwelling"
    state = project.state or "NSW"
    due_diligence = strip_due_diligence_contract_meta(
        _archetype_due_diligence_checklist(archetype, state=state)
    )
    authority_table = _nsw_authority_tracker_table(state, pack)
    heritage_controls = _render_heritage_controls(pack)
    return "\n".join(
        [
            "## Approvals and compliance",
            "",
            due_diligence,
            "",
            f"Planning pathway (fee proposal): {pack.planning_pathway or 'TBC — confirm CDC vs DA.'}",
            "",
            *(["", heritage_controls, ""] if heritage_controls else []),
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
    if pack.heritage_approval_advice:
        rows.append(
            "| Heritage impact statement | Partial | Architect-PM / heritage consultant | "
            "Prepare at schematic stage; allow 6-8 weeks council assessment |"
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
    programme_evidence = [
        *[f"Owner aspiration: {item}" for item in pack.owner_programme_aspirations],
        *([pack.builder_rom_programme] if pack.builder_rom_programme else []),
    ]
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
            *_optional_bullet_block("Programme evidence on file", programme_evidence),
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
    if pack.builder_rom:
        rom_items = [
            pack.builder_rom,
            *([pack.builder_rom_programme] if pack.builder_rom_programme else []),
            *[f"ROM caveat: {item}" for item in pack.builder_rom_caveats],
            *(
                [f"Conflict disclosure: {pack.builder_conflict_disclosure}"]
                if pack.builder_conflict_disclosure
                else []
            ),
        ]
        quote_block = ["", "**Builder ROM on file (market signal only):**", _bullet_lines(rom_items)]
    if pack.builder_quotes:
        quote_block.extend(
            ["", "**Builder pricing on file (unverified):**", _bullet_lines(pack.builder_quotes)]
        )
    contingency_line = (
        f"Owner-held contingency: {pack.owner_additional_contingency}"
        if pack.owner_additional_contingency
        else None
    )
    missing = ["elemental cost plan", "tender evaluation matrix"]
    if pack_has_gap(pack, GAP_MASTER_PROGRAMME):
        missing.insert(1, "master programme")
    missing_line = f"Missing artefacts: {', '.join(missing)}."
    conflict = pack.conflict_disclosure or pack.builder_conflict_disclosure or "None stated."
    return "\n".join(
        [
            "## Cost, programme and procurement posture",
            "",
            "HIA elemental / residential cost plan posture: contingency 5–10%; PC sums and "
            "owner-supplied items tracked separately.",
            budget_line,
            *([contingency_line] if contingency_line else []),
            *quote_block,
            "",
            "**Head-builder procurement:**",
            _bullet_lines(
                [
                    f"{pack.invited_builder_count or '2–3'} invited builders; "
                    f"{pack.formal_tender_count or '1'} formal head-builder tender assumed.",
                    f"Conflict disclosure before tender list lock: {conflict}",
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
            (
                "| Heritage consultant | Yes | Partial | Desktop advice on file; "
                "HIS to prepare at schematic stage |"
                if pack.heritage_advice
                else "| Heritage consultant | No | Assumption | Appoint if heritage controls apply |"
            ),
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
    if project_has_taxonomy(project):
        risk_rows = _taxonomy_risk_rows(project, pack)
    elif project.archetype == "renovation":
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
    if pack.owner_additional_contingency:
        facts.append(f"Owner contingency noted: {pack.owner_additional_contingency}")
    if pack.builder_rom:
        facts.append(pack.builder_rom)
    if pack.heritage_advice:
        facts.append(pack.heritage_advice)
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


def _fact_ledger_lines(pack: MobilisationEvidencePack) -> list[str]:
    if not pack.fact_ledger:
        return [f"  - {NARRATIVE_PLACEHOLDER}"]
    return [
        f"  - {entry.source} -> {entry.section}: {entry.fact}"
        for entry in pack.fact_ledger
    ]


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
            "- **Fact ledger**",
            *_fact_ledger_lines(pack),
            "- **Register rows**",
            f"  - {NARRATIVE_PLACEHOLDER}",
            "- **Workflow warnings**",
            *warning_lines,
        ]
    )


def _metadata_value(value: object) -> str:
    if value is None:
        return "TBC"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return f"{value:g}"
    if isinstance(value, list):
        return ", ".join(_metadata_value(item) for item in value) or "TBC"
    if isinstance(value, dict):
        return ", ".join(
            f"{key}: {_metadata_value(item)}"
            for key, item in value.items()
            if item not in (None, "", [], {})
        ) or "TBC"
    text = str(value).strip()
    return text or "TBC"


def _taxonomy_scale_summary(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        return "TBC"
    scale = ", ".join(
        f"{key} {_metadata_value(value)}" for key, value in context.scale.items()
    )
    subclass = ", ".join(context.subclasses) or "TBC"
    return f"{subclass}; {scale or 'scale TBC'}"


def _top_weighted_section_id(project: Project) -> str | None:
    context = pmp_taxonomy_context(project)
    if context is None:
        return None
    candidates = [
        (section_id, weight)
        for section_id, weight in context.section_weights.items()
        if section_id != "snapshot"
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])[0]


def _emphasis_note(project: Project, section_id: str) -> str:
    if _top_weighted_section_id(project) != section_id:
        return ""
    return (
        "Profile emphasis: this section carries the highest weighting for the selected "
        "taxonomy. Give it the most project-specific depth, retain concrete setup facts, "
        "and cut generic prose elsewhere before reducing this content."
    )


def _evidence_status_table() -> str:
    return "\n".join(
        [
            "| Topic | Status | Basis | Next action |",
            "| --- | --- | --- | --- |",
            "| Project setup | User provided | Project title and taxonomy fields | Confirm missing details |",
            "| Current corpus | Not evidenced | No uploaded project documents used in this scaffold | Upload brief, approvals, programme, and cost records |",
            "| Seed doctrine | Assumption | Curated platform seed sections | Replace assumptions as evidence arrives |",
        ]
    )


def _render_taxonomy_snapshot(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    fields = context.user_provided_fields
    rows = [
        "| Field | Value | Evidence status |",
        "| --- | --- | --- |",
        f"| Project | {_metadata_value(project.title)} | User provided |",
        f"| Site / address | {_metadata_value(fields.get('site_address'))} | User provided / Not evidenced |",
        f"| Client | {_metadata_value(fields.get('client'))} | User provided / Not evidenced |",
        f"| State | {_metadata_value(project.state or 'NSW')} | User provided |",
        f"| Taxonomy | {context.building_class} / {context.work_type or 'TBC'} | User provided |",
        f"| Subclass and scale | {_taxonomy_scale_summary(project)} | User provided |",
        f"| Budget | {_metadata_value(fields.get('budget'))} | User provided / Assumption |",
        f"| Timeframe | {_metadata_value(fields.get('timeframe'))} | User provided / Assumption |",
        f"| Procurement route | {_metadata_value(fields.get('procurement_route'))} | User provided / Assumption |",
    ]
    return "\n".join(
        [
            f"## {heading_for_section_id('snapshot', work_type=context.work_type)}",
            "",
            "\n".join(rows),
            "",
            _evidence_status_table(),
            "",
            "Scaffold status: this PMP is useful immediately from setup inputs, but every "
            "project-specific delivery claim remains open until current project documents "
            "are uploaded or the user confirms the assumption.",
        ]
    )


def _render_taxonomy_scope(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    scope_items = work_scope_items_for(context.work_type, context.work_scope)
    roster = [
        "| Scope item | Expected consultants | Evidence status |",
        "| --- | --- | --- |",
    ]
    if scope_items:
        for item in scope_items:
            roster.append(
                f"| {item.label} | {', '.join(item.consultants) or 'TBC'} | Assumption |"
            )
    else:
        roster.append("| Scope selection | Architect-PM / Project Manager | Assumption |")

    residential_note = (
        "For residential new work, confirm finishes, fixtures, wet-area scope, kitchen/bathroom "
        "allowances, appliance and tapware selections, flooring, joinery, external works, "
        "landscaping, utility connections, owner selections, and owner-supplied items before procurement. "
        "Keep finishes/fixtures explicit because this is where budget and expectation gaps "
        "usually appear."
        if context.building_class == "residential" and context.work_type == "new"
        else "Confirm the scope boundary, exclusions, interfaces, and client acceptance criteria before procurement or advisory delivery."
    )
    return "\n".join(
        [
            f"## {heading_for_section_id('scope-client-requirements', work_type=context.work_type)}",
            "",
            f"Class/type/subclass: **User provided** {context.building_class} / {context.work_type or 'TBC'} / {', '.join(context.subclasses) or 'TBC'}.",
            f"Scale summary: **User provided** {_taxonomy_scale_summary(project)}.",
            residential_note,
            "Any project-specific scope not yet supported by current corpus documents remains **Assumption** until uploaded evidence confirms it.",
            "Use this section as the control point for scope drift: record inclusions, "
            "exclusions, interfaces, owner/client decisions, and consultant information "
            "requests before procurement or service delivery starts.",
            _emphasis_note(project, "scope-client-requirements"),
            "",
            "\n".join(roster),
        ]
    )


def _render_taxonomy_compliance(project: Project, seed_section_refs: dict[str, tuple[str, ...]] | None) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    refs = seed_section_refs.get("compliance-approvals", ()) if seed_section_refs else ()
    rows = [
        "| Approval / compliance item | Status | Basis | Next action |",
        "| --- | --- | --- | --- |",
        "| NCC pathway | Assumption | Taxonomy and loaded seed doctrine | Confirm DtS/performance pathway with certifier |",
        "| Authority approvals | Not evidenced | No current approval records used | Upload planning/approval records |",
        "| Essential safety measures | Assumption | Seed doctrine | Confirm ESM schedule where applicable |",
    ]
    if "fire_services" in context.work_scope:
        rows.extend(
            [
                "| Fire hydrant systems | Assumption | AS 2419.1 seed reference | Confirm hydrant scope and authority requirements |",
                "| Fire pumpsets | Assumption | AS 2941 seed reference | Confirm pumpset duty, redundancy, and commissioning pathway |",
            ]
        )
    ref_line = f"Loaded seed sections: {', '.join(refs)}." if refs else "Loaded seed sections: TBC."
    return "\n".join(
        [
            f"## {heading_for_section_id('compliance-approvals', work_type=context.work_type)}",
            "",
            ref_line,
            "Do not use generic compliance prose where a required seed section is absent; mark the gap for user confirmation.",
            "The approval pathway, certifier position, authority inputs, and inspection or "
            "commissioning hold points are **Not evidenced** until the current corpus "
            "contains approval records, consultant advice, or authority correspondence.",
            _emphasis_note(project, "compliance-approvals"),
            "",
            "\n".join(rows),
        ]
    )


def _render_taxonomy_programme(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    return "\n".join(
        [
            f"## {heading_for_section_id('programme', work_type=context.work_type)}",
            "",
            "| Milestone | Status | Evidence basis | Next action |",
            "| --- | --- | --- | --- |",
            "| Setup / brief confirmation | User provided | Taxonomy setup | Confirm scope and budget lock |",
            "| Authority pathway | Assumption | Seed doctrine | Confirm approval route and lead times |",
            "| Procurement / services start | Assumption | Work type and role | Confirm procurement or advisory deliverables programme |",
            "| Delivery / reporting cadence | Not evidenced | No programme document used | Upload programme or agree reporting cadence |",
            "",
            "Programme logic should stay milestone-based until a current programme is uploaded. "
            "Authority lead times, live-environment staging, shutdown windows, and client "
            "review periods are assumptions that need confirmation before dates are issued.",
            _emphasis_note(project, "programme"),
        ]
    )


def _render_taxonomy_cost(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    budget = context.user_provided_fields.get("budget")
    risk_text = "; ".join(flag.title for flag in context.risk_flags) or "No derived uplift flags"
    return "\n".join(
        [
            f"## {heading_for_section_id('cost-budget', work_type=context.work_type)}",
            "",
            f"Budget: **User provided / Assumption** {_metadata_value(budget)}.",
            f"Complexity/risk uplift watch: **Assumption** {risk_text}.",
            "Cost plan, contingency, PC/PS allowances, and benchmark basis are **Not evidenced** until current project documents are uploaded.",
            "Use companion cost/risk annexures for detailed line items; keep the primary PMP to budget status, constraints, and decisions.",
            "Before commitment, confirm whether the stated budget covers consultants, authority "
            "fees, escalation, contingency, temporary works, and risk allowances triggered by "
            "the selected complexity profile.",
            _emphasis_note(project, "cost-budget"),
        ]
    )


def _render_taxonomy_procurement(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    if context.work_type == "advisory":
        rows = [
            "| Deliverable | Status | Next action |",
            "| --- | --- | --- |",
            "| Technical due diligence / review output | Assumption | Confirm report format and review hold points |",
            "| Exclusions and reliance limits | Assumption | Confirm in engagement scope |",
            "| Evidence request list | Not evidenced | Issue document request register |",
        ]
    else:
        rows = [
            "| Procurement / delivery item | Status | Next action |",
            "| --- | --- | --- |",
            "| Procurement route | User provided / Assumption | Confirm contract and tender pathway |",
            "| Consultant inputs | Assumption | Appoint or confirm discipline roster |",
            "| Tender / award gates | Not evidenced | Upload procurement programme and evaluation criteria |",
        ]
    return "\n".join(
        [
            f"## {heading_for_section_id('procurement-delivery', work_type=context.work_type)}",
            "",
            "\n".join(rows),
            "",
            "Delivery responsibilities remain an **Assumption** until appointment documents "
            "confirm who decides, who advises, who certifies, who contracts, and who carries "
            "coordination risk for each work-scope item.",
            _emphasis_note(project, "procurement-delivery"),
        ]
    )


def _render_taxonomy_risks(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    rows = ["| Risk | Owner | Status | Next action | Due |", "| --- | --- | --- | --- | --- |"]
    for risk, owner, status, action, due in _taxonomy_risk_rows(project):
        rows.append(f"| {risk} | {owner} | {status} | {action} | {due} |")
    return "\n".join(
        [
            f"## {heading_for_section_id('risks', work_type=context.work_type)}",
            "",
            "\n".join(rows),
            "",
            "Primary risk register is capped at 8 rows. Full risk detail belongs in a companion annexure.",
            "Risk status is deliberately conservative in scaffold mode: selected complexity "
            "options create risk rows, but severity and mitigation should be recalibrated "
            "when the current corpus contains consultant advice, authority records, or cost "
            "evidence.",
            _emphasis_note(project, "risks"),
        ]
    )


def _decision_block(block_id: str, label: str, prompt: str) -> str:
    return "\n".join(
        [
            "```pmp-decision",
            "{",
            f'  "id": "{block_id}",',
            f'  "label": "{label}",',
            f'  "prompt": "{prompt}",',
            '  "selected": "decision-required",',
            '  "source": "agent",',
            '  "options": [',
            '    {"value": "decision-required", "label": "Decision required"},',
            '    {"value": "confirmed", "label": "Confirmed"},',
            '    {"value": "defer", "label": "Defer"}',
            "  ]",
            "}",
            "```",
        ]
    )


def _render_taxonomy_actions(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    actions = [
        "| Action / decision | Owner | Status | Next action |",
        "| --- | --- | --- | --- |",
        "| Confirm scope boundary and exclusions | Owner | User provided / Assumption | Lock client requirements before procurement |",
        "| Confirm approval pathway | Architect-PM | Assumption | Test NCC/authority path with certifier |",
        "| Confirm budget and contingency basis | Owner | Assumption | Provide budget or cost plan evidence |",
        "| Confirm consultant roster | Architect-PM | Assumption | Appoint required disciplines from work-scope list |",
    ]
    return "\n".join(
        [
            f"## {heading_for_section_id('actions-decisions', work_type=context.work_type)}",
            "",
            "\n".join(actions),
            "",
            "Decision blocks below are placeholders for the user to lock the PMP basis. "
            "Locked decisions should survive refreshes; conflicting uploaded evidence should "
            "create a visible action rather than silently changing the taxonomy or section "
            "weighting.",
            _emphasis_note(project, "actions-decisions"),
            "",
            _decision_block("scope-boundary", "Scope boundary", "Confirm the scope boundary and exclusions."),
            "",
            _decision_block("approval-pathway", "Approval pathway", "Confirm the approval and certification pathway."),
            "",
            _decision_block("budget-basis", "Budget basis", "Confirm the budget, contingency, and cost-plan basis."),
            "",
            _decision_block("consultant-roster", "Consultant roster", "Confirm the required consultant roster."),
        ]
    )


def _render_taxonomy_platform_scaffold(
    project: Project,
    *,
    seed_section_refs: dict[str, tuple[str, ...]] | None = None,
) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    sections = [
        _render_taxonomy_snapshot(project),
        _render_taxonomy_scope(project),
        _render_taxonomy_compliance(project, seed_section_refs),
        _render_taxonomy_programme(project),
        _render_taxonomy_cost(project),
        _render_taxonomy_procurement(project),
        _render_taxonomy_risks(project),
        _render_taxonomy_actions(project),
    ]
    rendered_headings = {
        line.strip()[3:].strip().lower()
        for section in sections
        for line in section.splitlines()
        if line.strip().startswith("## ")
    }
    missing = [
        heading
        for heading in pmp_section_headings(work_type=context.work_type)
        if heading.lower() not in rendered_headings
    ]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"PMP scaffold missing required sections: {joined}")
    title = document_title_for_role(
        project.user_role or "architect-pm",
        project=project,
    )
    return f"# {title}\n\n" + "\n\n".join(sections) + "\n"


def render_pmp_scaffold(
    project: Project,
    pack: MobilisationEvidencePack,
    draft_mode: DraftMode,
    *,
    version: int = 1,
    seed_section_refs: dict[str, tuple[str, ...]] | None = None,
) -> str:
    """Render deterministic PMP markdown scaffold from project overlays and evidence pack."""
    if draft_mode == "platform_seeded" and project_has_taxonomy(project):
        return _render_taxonomy_platform_scaffold(
            project,
            seed_section_refs=seed_section_refs,
        )

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

    headings = required_section_headings(user_role, project=project)
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

    title = document_title_for_role(user_role, project=project)
    body = "\n\n".join(sections)
    return f"# {title}\n\n{body}\n"
