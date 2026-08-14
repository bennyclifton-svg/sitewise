"""Deterministic PMP scaffold rendering from a MobilisationEvidencePack."""

from __future__ import annotations

import re
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
from app.sitewise.pmp_citations import (
    CitationIndex,
    build_citation_index,
    format_citation_key_lines,
)
from app.sitewise.pmp_greenfield_brief import (
    ARCHITECT_PM_PROGRAMME_SUBMILESTONE_TABLE,
    RISK_REGISTER_TABLE,
    _archetype_due_diligence_checklist,
    programme_submilestone_table,
    strip_due_diligence_contract_meta,
)
from app.sitewise.pmp_sources import document_title, required_section_headings
from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context, project_has_taxonomy
from app.sitewise.section_contracts import heading_for_section_id, pmp_section_headings
from app.sitewise.taxonomy import (
    DESIGN_LEAD_UNCONFIRMED,
    DESIGN_LEAD_UNCONFIRMED_LABEL,
    building_class_label,
    design_lead_discipline,
    scale_field_label,
    subclass_label,
    work_scope_items_for,
    work_type_label,
)

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
            "Architect",
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
            "Architect",
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

    lead = design_lead_discipline(context.work_type, context.work_scope)
    owner = "TBC" if lead == DESIGN_LEAD_UNCONFIRMED else lead
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
                owner,
                "Not evidenced",
                "Upload brief, authority, cost, programme, and consultant records",
                "TBC",
            ),
            (
                "Consultant and approval pathway unresolved",
                owner,
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
            owner,
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
    live_status = (
        "Partial" if "live occupation" in live_signal.lower() else "Assumption"
    )
    return (
        (
            "Latent conditions in existing footings / masonry tie-ins",
            "Architect",
            "Assumption",
            "Allow contingency / provisional sums; stage investigation before scheme lock",
            "TBC",
        ),
        (
            "Heritage / conservation-area controls",
            "Architect",
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
            "Architect to coordinate owner's appointment of consultants "
            "(owner-commissioned per engagement)",
            "TBC",
        ),
        (
            "Builder conflict / related-party tender",
            "Architect",
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
            f"Archetype: {project.archetype or 'TBC'}. "
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
        "| Architect (advisory) | Yes | Per executed engagement letter |"
        if engaged
        else "| Architect (advisory) | Declared (project overlay) | "
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
        f"PI insurance: {pack.pi_holder or pack.appointee or 'Architect'} holds policy "
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
            "## Architect role and appointment",
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
            _labeled_field("**Owner project brief**", pack.dwelling_summary)
            if pack.dwelling_summary
            else ""
        )
    else:
        owner_brief_line = ""
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
            *([owner_brief_line] if owner_brief_line else []),
            "Extra tender round = engagement variation; material scope change = owner project brief "
            "+ decision register entry.",
        ]
    )


def _render_governance(pack: MobilisationEvidencePack) -> str:
    raci = "\n".join(
        [
            "| Activity | Owner | Architect | Consultants | Builder | Certifier |",
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
    scope_prefix = "Building scope"
    return "\n".join(
        [
            "## Scope and change control",
            "",
            _labeled_field(scope_prefix, pack.dwelling_summary),
            _labeled_field("Site / planning constraints", pack.site_constraints),
            *_optional_bullet_block(
                "Owner design objectives", pack.owner_brief_objectives
            ),
            *_optional_bullet_block(
                "Heritage design constraints", pack.heritage_design_advice
            ),
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
    if not (
        pack.heritage_context
        or pack.heritage_approval_advice
        or pack.heritage_design_advice
    ):
        return ""
    lines = ["### Heritage / character controls"]
    if pack.heritage_context:
        lines.append(_labeled_field("Status", pack.heritage_context))
    if pack.heritage_approval_advice:
        lines.append(_labeled_field("Approval advice", pack.heritage_approval_advice))
    if pack.heritage_design_advice:
        lines.extend(
            ["", "**Design controls:**", _bullet_lines(pack.heritage_design_advice)]
        )
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
            "| BASIX (commitment) | Assumption | Owner / Architect | Appoint assessor; align with DA |"
        )
    if pack.heritage_approval_advice:
        rows.append(
            "| Heritage impact statement | Partial | Architect / heritage consultant | "
            "Prepare at schematic stage; allow 6-8 weeks council assessment |"
        )
    certifier_status = (
        "Partial" if not pack_has_gap(pack, GAP_CERTIFIER) else "Assumption"
    )
    certifier_action = (
        "Appointed — coordinate CC pathway"
        if not pack_has_gap(pack, GAP_CERTIFIER)
        else "Appoint before CC"
    )
    rows.extend(
        [
            f"| Principal certifier | {certifier_status} | Owner | {certifier_action} |",
            f"| DA / planning permit | {da_status} | Owner / Architect | {da_action} |",
            "| Construction Certificate | Assumption | Certifier | Issue before site start |",
            "| LSL receipt | Assumption | Builder | CC-blocking prerequisite |",
            f"| Utility connections ({state}) | Assumption | Owner / builder | Confirm capacity |",
            "| Occupation Certificate | Assumption | Certifier | Issue at handover |",
        ]
    )
    return "\n".join(rows)


def _render_programme(pack: MobilisationEvidencePack) -> str:
    submilestone_block = programme_submilestone_table()
    submilestone_table = _table_lines_from_brief(
        submilestone_block
    ) or _table_lines_from_brief(ARCHITECT_PM_PROGRAMME_SUBMILESTONE_TABLE)
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
            *_optional_bullet_block("Programme evidence", programme_evidence),
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
            budget_line = "Assumption: construction budget not evidenced — owner to confirm working budget ceiling."
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
        quote_block = [
            "",
            "**Builder ROM on file (market signal only):**",
            _bullet_lines(rom_items),
        ]
    if pack.builder_quotes:
        quote_block.extend(
            [
                "",
                "**Builder pricing on file (unverified):**",
                _bullet_lines(pack.builder_quotes),
            ]
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
    conflict = (
        pack.conflict_disclosure or pack.builder_conflict_disclosure or "None stated."
    )
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
        "Appointed" if not pack_has_gap(pack, GAP_CERTIFIER) else "Assumption"
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
                f"| Architect ({pack.appointee or 'Architect'}) | Yes | Executed "
                f"{pack.engagement_executed_date or 'TBC'} | Engagement letter on file |"
                if has_engagement_evidence(pack)
                else f"| Architect ({pack.appointee or 'Architect'}) | Declared | "
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
        if (
            pack_has_gap(pack, GAP_CONSTRUCTION_BUDGET) is False
            and "budget not evidenced" in risk.lower()
        ):
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
    holder = pack.pi_holder or "Architect"
    facts: list[str] = [
        (
            f"{holder} engaged as architect-PM; engagement executed "
            f"{pack.engagement_executed_date or 'TBC'}."
            if engaged
            else "Architect role declared on the project record; executed engagement "
            "letter not on file."
        ),
    ]
    if pack.owner_brief_on_file and not pack_has_gap(pack, GAP_OWNER_BRIEF):
        signed = pack.owner_brief_signed_date or "on file"
        facts.append(f"Owner project brief signed {signed}.")
    if pack.construction_budget_ceiling and not pack_has_gap(
        pack, GAP_CONSTRUCTION_BUDGET
    ):
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
        facts.append(
            f"Target DA lodgement {pack.target_da_lodgement} per engagement letter."
        )
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
    assumptions = [f"Assumption: {gap}." for gap in pack.gaps] or [
        "Assumption: none identified."
    ]
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
        return (
            ", ".join(
                f"{key}: {_metadata_value(item)}"
                for key, item in value.items()
                if item not in (None, "", [], {})
            )
            or "TBC"
        )
    text = str(value).strip()
    return text or "TBC"


def _taxonomy_scale_summary(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        return ""
    subclass = ", ".join(
        subclass_label(context.building_class, value) for value in context.subclasses
    )
    scale = ", ".join(
        f"{scale_field_label(context.building_class, context.subclasses, key)} "
        f"{_metadata_value(value)}"
        for key, value in context.scale.items()
        if value not in (None, "", [], {})
    )
    return "; ".join(part for part in (subclass, scale) if part)


def _class_type_subclass_line(context) -> str:
    parts = [
        building_class_label(context.building_class),
        work_type_label(context.work_type),
        ", ".join(
            subclass_label(context.building_class, value)
            for value in context.subclasses
        ),
    ]
    return " / ".join(part for part in parts if part)


def _top_weighted_section_id(project: Project) -> str | None:
    context = pmp_taxonomy_context(project)
    if context is None:
        return None
    candidates = [
        (section_id, weight)
        for section_id, weight in context.section_weights.items()
        if section_id not in {"snapshot", "citation-key"}
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])[0]


def _citation_index_from_pack(pack: MobilisationEvidencePack | None) -> CitationIndex:
    if pack is None or not pack.evidence_refs:
        return build_citation_index([])
    return build_citation_index([(ref, "on file") for ref in pack.evidence_refs])


_ENGAGEMENT_REF_PATTERNS: tuple[str, ...] = (
    "letter of engagement",
    "letter-of-engagement",
    "letter_of_engagement",
    "engagement letter",
    "engagement-letter",
    "engagement_letter",
    "letter of appointment",
    "letter-of-appointment",
    "letter_of_appointment",
    "appointment letter",
    "appointment-letter",
    "appointment_letter",
)

_FEE_REF_PATTERNS: tuple[str, ...] = (
    "fee proposal",
    "fee-proposal",
    "fee_proposal",
    "fees proposal",
    "fee quote",
    "fee-quote",
    "fee_quote",
)


def _ref_match_key(ref: str) -> str:
    return ref.replace("\\", "/").lower()


def _best_ref_for_patterns(
    refs: list[str],
    patterns: tuple[str, ...],
) -> str | None:
    """Return the highest-scoring ref for the given patterns, or None."""
    best_ref: str | None = None
    best_score = 0
    for ref in refs:
        key = _ref_match_key(ref)
        for index, pattern in enumerate(patterns):
            if pattern not in key:
                continue
            # Earlier / more specific patterns score higher.
            score = len(patterns) - index
            if score > best_score:
                best_score = score
                best_ref = ref
    return best_ref


def _engagement_citation_token(
    pack: MobilisationEvidencePack,
    citation_index: CitationIndex,
) -> str:
    """Prefer engagement/appointment letter, then fee proposal, else dash.

    Matches real filenames such as ``Letter of Engagement.pdf`` and
    ``letter-of-appointment.pdf``, not only kebab-slug forms.
    """
    refs = list(pack.evidence_refs)
    if not refs:
        return "—"

    engagement_ref = _best_ref_for_patterns(refs, _ENGAGEMENT_REF_PATTERNS)
    if engagement_ref is not None:
        return citation_index.token_for(engagement_ref)

    fee_ref = _best_ref_for_patterns(refs, _FEE_REF_PATTERNS)
    if fee_ref is not None:
        return citation_index.token_for(fee_ref)

    # Last resort when engagement facts exist: any plausible engagement/fee hint.
    if has_engagement_evidence(pack):
        for ref in refs:
            key = _ref_match_key(ref)
            if "engagement" in key or "appointment" in key or "fee" in key:
                return citation_index.token_for(ref)

    return "—"


def _emphasis_note(project: Project, section_id: str) -> str:
    if _top_weighted_section_id(project) != section_id:
        return ""
    return (
        "Profile emphasis: this section carries the highest weighting for the selected "
        "taxonomy. Give it the most project-specific depth, retain concrete setup facts, "
        "and cut generic prose elsewhere before reducing this content."
    )


def render_project_summary_table(
    project: Project,
    *,
    project_title: str | None = None,
    project_title_source: str = "Profile",
    site_address: str | None = None,
    client: str | None = None,
    site_address_status: str = "Profile / Not evidenced",
    site_address_citation: str = "—",
    client_status: str = "Profile / Not evidenced",
    client_citation: str = "—",
    budget: str | None = None,
    budget_source: str | None = None,
    compact_sources: bool = False,
    profile_citation: str = "",
) -> str:
    """Render the shared project-summary table used by PMP-derived artefacts."""
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("project summary requires project taxonomy")
    fields = context.user_provided_fields
    taxonomy_value = f"{context.building_class} / {context.work_type or 'TBC'}"
    if compact_sources:
        project_value = project_title or _metadata_value(project.title)
        site_value = site_address or _metadata_value(fields.get("site_address"))
        client_value = client or _metadata_value(fields.get("client"))
        budget_value = budget or _metadata_value(fields.get("budget"))
        timeframe_value = _metadata_value(fields.get("timeframe"))
        procurement_value = _metadata_value(fields.get("procurement_route"))
        return _summary_table_markdown(
            [
                f"| Project | {project_value} | {project_title_source} |",
                f"| Site / address | {site_value} | {_compact_summary_source(site_value, site_address_citation)} |",
                f"| Client | {client_value} | {_compact_summary_source(client_value, client_citation)} |",
                f"| State | {_metadata_value(project.state or 'NSW')} | Profile |",
                f"| Taxonomy | {taxonomy_value} | Profile |",
                f"| Subclass and scale | {_compact_taxonomy_scale_summary(project)} | Profile |",
                f"| Budget | {budget_value} | {budget_source or _compact_summary_source(budget_value)} |",
                f"| Timeframe | {timeframe_value} | {_compact_summary_source(timeframe_value)} |",
                f"| Procurement route | {procurement_value} | {_compact_summary_source(procurement_value)} |",
            ]
        )
    profile_cell = _citation_cell(profile_citation)
    return _summary_table_markdown(
        [
            (
                f"| Project | {_metadata_value(project_title or project.title)} | "
                f"{_citation_cell(project_title_source) or profile_cell} |"
            ),
            (
                f"| Site / address | "
                f"{site_address or _metadata_value(fields.get('site_address'))} | "
                f"{_citation_cell(site_address_citation) or profile_cell} |"
            ),
            (
                f"| Client | {client or _metadata_value(fields.get('client'))} | "
                f"{_citation_cell(client_citation) or profile_cell} |"
            ),
            f"| State | {_metadata_value(project.state or 'NSW')} | {profile_cell} |",
            f"| Taxonomy | {taxonomy_value} | {profile_cell} |",
            (
                f"| Subclass and scale | {_compact_taxonomy_scale_summary(project)} | "
                f"{profile_cell} |"
            ),
            (
                f"| Budget | {_metadata_value(budget or fields.get('budget'))} | "
                f"{_citation_cell(budget_source or '')} |"
            ),
            f"| Timeframe | {_metadata_value(fields.get('timeframe'))} |  |",
            f"| Procurement route | {_metadata_value(fields.get('procurement_route'))} |  |",
        ]
    )


def _citation_cell(citation: str) -> str:
    """Render an empty citation cell when no source token is available."""
    value = citation.strip()
    if re.fullmatch(r"\[\d+\](?:\s+\[\d+\])*", value) is None:
        return ""
    return value


def _summary_table_markdown(rows: list[str]) -> str:
    """Build a GFM table without a column-label header row.

    The first data row is used as the GFM header line so the table still parses;
    presentation and export demote that row to body styling.
    """
    if not rows:
        return ""
    return "\n".join([rows[0], "| --- | --- | --- |", *rows[1:]])


def _compact_summary_source(value: str, citation: str = "—") -> str:
    if citation != "—":
        return citation
    return "Confirm" if value == "TBC" else "Profile"


_COMPACT_SCALE_LABELS = {
    "gfa_sqm": ("GFA", "m²"),
    "nla_sqm": ("NLA", "m²"),
    "floor_plate_sqm": ("floor plate", "m²"),
    "office_percent": ("office", "%"),
}
_COMPACT_COUNT_LABELS = {
    "storeys": ("storey", "storeys"),
    "tenancies": ("tenancy", "tenancies"),
    "dwellings": ("dwelling", "dwellings"),
    "bedrooms": ("bedroom", "bedrooms"),
    "garage_spaces": ("garage space", "garage spaces"),
}


def _compact_taxonomy_scale_summary(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        return ""
    subclass = ", ".join(
        subclass_label(context.building_class, value) for value in context.subclasses
    )
    parts = [subclass] if subclass else []
    for key, value in context.scale.items():
        if value in (None, "", [], {}) or str(value).strip().lower() == "not declared":
            continue
        label, unit = _COMPACT_SCALE_LABELS.get(
            key,
            (
                scale_field_label(context.building_class, context.subclasses, key),
                "",
            ),
        )
        rendered = _metadata_value(value)
        if key in _COMPACT_COUNT_LABELS and isinstance(value, (int, float)):
            singular, plural = _COMPACT_COUNT_LABELS[key]
            parts.append(f"{rendered} {singular if value == 1 else plural}")
        elif key == "office_percent":
            parts.append(f"{rendered}% {label}")
        elif unit:
            parts.append(f"{rendered} {unit} {label}")
        else:
            parts.append(f"{rendered} {label}")
    return "; ".join(part for part in parts if part)


def _taxonomy_project_description(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        return "Not provided"
    for key in ("brief", "notes"):
        value = context.user_provided_fields.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    scope_items = work_scope_items_for(context.work_type, context.work_scope)
    narrative = _scope_narrative(project)
    if scope_items or narrative:
        # The user's own wording leads. A reader recognises "concrete cancer in
        # the basement carpark"; they do not recognise "Facade/Cladding
        # Rectification", which is a routing key that happens to be printable.
        scope = "; ".join(narrative or [item.label for item in scope_items])
        work_type = work_type_label(context.work_type) or "Project"
        asset = _compact_taxonomy_scale_summary(project)
        lead = f"{work_type} works for {asset}" if asset else f"{work_type} works"
        return (
            f"{lead}. Scope includes {scope}. "
            "This plan coordinates approvals, consultants, cost, programme, "
            "procurement, risks, owner decisions, and delivery close-out."
        )
    project_type = " ".join(
        part
        for part in (
            work_type_label(context.work_type),
            building_class_label(context.building_class),
        )
        if part
    )
    if not project_type:
        return "Not provided"
    missing: list[str] = []
    if not context.user_provided_fields.get("site_address"):
        missing.append("site")
    if not context.subclasses and not context.scale:
        missing.append("asset")
    if not scope_items and not narrative:
        missing.append("scope")
    base = (
        f"{project_type} project. This plan establishes the brief, "
        "approvals, consultant, cost, programme, procurement, risk, and owner-decision "
        "controls."
    )
    if not missing:
        return base
    return f"{base} {_unstated_details_clause(missing)}"


def _unstated_details_clause(missing: list[str]) -> str:
    if len(missing) == 1:
        head = missing[0]
    elif len(missing) == 2:
        head = f"{missing[0]} and {missing[1]}"
    else:
        head = f"{missing[0]}, {missing[1]}, and {missing[2]}"
    return (
        f"{head[0].upper()}{head[1:]} details remain to be confirmed from the "
        "project profile or current evidence."
    )


def _summary_detail(value: object) -> str:
    return _metadata_value(value) if value not in (None, "", [], {}) else "Not provided"


def _render_taxonomy_snapshot(
    project: Project,
    *,
    citation_index: CitationIndex | None = None,
) -> str:
    del (
        citation_index
    )  # reserved for grounded summary fields; profile rows need no citation
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    fields = context.user_provided_fields
    rows = _summary_table_markdown(
        [
            f"| Project | {_summary_detail(project.title)} |  |",
            f"| Address | {_summary_detail(fields.get('site_address'))} |  |",
            f"| Owner | {_summary_detail(fields.get('client'))} |  |",
            f"| Description | {_taxonomy_project_description(project)} |  |",
        ]
    )
    return "\n".join(
        [
            f"## {heading_for_section_id('snapshot', work_type=context.work_type)}",
            "",
            rows,
            "",
            "Scaffold status: this PMP is useful immediately from setup inputs, but every "
            "project-specific delivery claim remains open for owner review until current "
            "project documents are uploaded or the user confirms the assumption.",
        ]
    )


def _scope_narrative(project: Project) -> list[str]:
    from app.projects.profile import project_scope_narrative

    return project_scope_narrative(project)


def _render_taxonomy_scope(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    scope_items = work_scope_items_for(context.work_type, context.work_scope)
    # The enum labels say which disciplines and doctrine apply; the narrative
    # says what the job actually is. "Building Services Upgrade" and "two 30-year-old
    # R22 units in the service centre and western office" are both needed, and only
    # the second is what the client recognises as their project.
    inclusions = [f"- {item.label}" for item in scope_items]
    inclusions.extend(f"- {item}" for item in _scope_narrative(project))
    if not inclusions:
        inclusions = ["- Scope selection pending — confirm inclusions with the client."]
    brief_is_emphasis = _top_weighted_section_id(project) == "scope-client-requirements"

    if context.building_class == "residential" and context.work_type == "new":
        residential_note = (
            "For residential new work, confirm finishes, fixtures, wet-area scope, kitchen/bathroom "
            "allowances, appliance and tapware selections, flooring, joinery, external works, "
            "landscaping, utility connections, owner selections, and owner-supplied items before procurement. "
            "Keep finishes/fixtures explicit because this is where budget and expectation gaps "
            "usually appear."
        )
    elif brief_is_emphasis:
        residential_note = (
            "Confirm the scope boundary, exclusions, interfaces, finishes/fixtures where relevant, "
            "and client acceptance criteria before procurement or advisory delivery."
        )
    else:
        residential_note = "Confirm inclusions, exclusions, interfaces, and acceptance criteria before procurement."

    scale_summary = _taxonomy_scale_summary(project)
    lines = [
        f"## {heading_for_section_id('scope-client-requirements', work_type=context.work_type)}",
        "",
        f"Class/type/subclass: {_class_type_subclass_line(context)}.",
    ]
    if scale_summary:
        lines.append(f"Scale summary: {scale_summary}.")
    lines.extend(
        [
            residential_note,
            "Project-specific scope that is not established by the current profile or corpus "
            "remains **Assumption** until clarified through design coordination and recorded "
            "owner decisions.",
            _emphasis_note(project, "scope-client-requirements"),
            "",
            "**Inclusions (work scope):**",
            "\n".join(inclusions),
        ]
    )
    if brief_is_emphasis or (
        context.building_class == "residential" and context.work_type == "new"
    ):
        lines.extend(
            [
                "",
                "**Exclusions / interfaces:** Assumption — confirm out-of-scope items and interfaces "
                "with the client, adjacent tenants, or separate packages.",
                "",
                "**Acceptance criteria / brief lock:** Assumption — lock client acceptance criteria "
                "before design freeze or tender.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "**Exclusions / interfaces / acceptance:** Assumption — confirm before tender.",
            ]
        )
    return "\n".join(lines)


def _asset_ffe_items(project: Project) -> list[dict[str, str]]:
    """Profile asset-register rows as FFE items (equipment on the unified table)."""
    from app.projects.profile import project_assets
    from app.sitewise.taxonomy import asset_option_label

    items: list[dict[str, str]] = []
    for asset in project_assets(project):
        condition = asset_option_label("condition", asset.condition)
        action = asset_option_label("action", asset.action)
        notes = "; ".join(
            part
            for part in (
                f"{asset.age_years} years old" if asset.age_years is not None else None,
                f"Replace with {asset.replacement_spec}"
                if asset.replacement_spec
                else None,
                asset.notes,
            )
            if part
        )
        items.append(
            {
                "item": asset.type,
                "location": asset.location or "—",
                "quantity": str(asset.count) if asset.count is not None else "—",
                "finish": asset.capacity or asset.make_model or "—",
                "status": action or condition or "User provided",
                "notes": notes or "—",
            }
        )
    return items


def _asset_schedule_rows(project: Project) -> list[str]:
    """Render the profile's asset register into the FFE table."""
    return [_ffe_markdown_row(item) for item in _asset_ffe_items(project)]


def _ffe_markdown_row(item: dict[str, str]) -> str:
    return (
        "| {item} | {location} | {quantity} | {finish} | {status} | {notes} |".format(
            item=item["item"],
            location=item.get("location") or "—",
            quantity=item.get("quantity") or "—",
            finish=item.get("finish") or "TBC",
            status=item.get("status") or "To be confirmed",
            notes=item.get("notes") or "—",
        )
    )


def _merge_ffe_items(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    merged: list[dict[str, str]] = []
    for group in groups:
        for item in group:
            key = str(item.get("item") or "").strip().casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _render_taxonomy_ffe_schedule(project: Project) -> str:
    from app.sitewise.ffe_schedule import ffe_schedule_rows
    from app.sitewise.ffe_typical import typical_ffe_rows

    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    explicit_items = ffe_schedule_rows(project)
    asset_items = _asset_ffe_items(project)
    typical_items = typical_ffe_rows(
        work_type=context.work_type,
        work_scope=context.work_scope,
        subclasses=context.subclasses,
    )
    if asset_items:
        typical_items = [
            item for item in typical_items if item["item"] != "HVAC plant"
        ]
    display_items = _merge_ffe_items(explicit_items, asset_items, typical_items)
    table = [
        "| Item | Location | Qty | Finish | Status | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    table.extend(_ffe_markdown_row(item) for item in display_items)
    if not display_items:
        table.append(
            "| — | — | — | — | To be confirmed | No finishes, fixtures or "
            "equipment recorded yet — add items in chat |"
        )
    return "\n".join(
        [
            f"## {heading_for_section_id('ffe-schedule', work_type=context.work_type)}",
            "",
            "Unified Finishes, Fixtures and Equipment register for interior and "
            "exterior finishes, fixtures, and plant. Add or tidy rows in chat. "
            "Missing selections stay TBC.",
            _emphasis_note(project, "ffe-schedule"),
            "",
            "\n".join(table),
        ]
    )


def _render_taxonomy_consultants(
    project: Project,
    pack: MobilisationEvidencePack | None = None,
    *,
    citation_index: CitationIndex | None = None,
) -> str:
    from app.sitewise.consultant_register import consultant_appointment_rows

    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    index = citation_index or build_citation_index([])
    pack = pack or MobilisationEvidencePack()
    rows = [
        "| Discipline | Firm | Fee | Status | Citation |",
        "| --- | --- | --- | --- | --- |",
    ]
    appointment_rows = {
        row["discipline"].strip().lower(): row
        for row in consultant_appointment_rows(project)
    }

    lead = design_lead_discipline(context.work_type, context.work_scope)
    engaged = has_engagement_evidence(pack)
    fee_known = has_fee_proposal_evidence(pack) or bool(pack.fee_total_ex_gst)
    seen: set[str] = set()
    if lead != DESIGN_LEAD_UNCONFIRMED:
        lead_fact = appointment_rows.get(lead.strip().lower())
        if engaged:
            firm = pack.appointee or lead
            fee = pack.fee_total_ex_gst or ("Per fee proposal" if fee_known else "TBC")
            status = "Partial"
            citation = _engagement_citation_token(pack, index)
        elif lead_fact:
            firm = str(lead_fact["firm"])
            fee = str(lead_fact.get("fee") or "")
            status = str(lead_fact["status"])
            citation = "—"
        else:
            firm = pack.appointee or "TBC"
            fee = "TBC"
            status = "Assumption"
            citation = "—"
        rows.append(f"| {lead} | {firm} | {fee} | {status} | {citation} |")
        seen.add(lead.strip().lower())
    for item in work_scope_items_for(context.work_type, context.work_scope):
        for consultant in item.consultants:
            key = consultant.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            fact = appointment_rows.get(key)
            if fact is None:
                # Soft match Services Engineer (Hydraulic) etc.
                fact = next(
                    (
                        row
                        for label, row in appointment_rows.items()
                        if label in key or key in label
                    ),
                    None,
                )
            if fact is not None:
                rows.append(
                    f"| {consultant} | {fact['firm']} | {fact.get('fee') or ''} | "
                    f"{fact['status']} | — |"
                )
                seen.add(str(fact["discipline"]).strip().lower())
            else:
                rows.append(
                    f"| {consultant} | TBC | | Not evidenced | — |"
                )
    for label, fact in appointment_rows.items():
        if label in seen:
            continue
        rows.append(
            f"| {fact['discipline']} | {fact['firm']} | {fact.get('fee') or ''} | "
            f"{fact['status']} | — |"
        )
    if len(rows) == 2:
        rows.append(
            "| Discipline roster | TBC | | Not evidenced | — |"
        )

    if lead == DESIGN_LEAD_UNCONFIRMED:
        intro = (
            f"{DESIGN_LEAD_UNCONFIRMED_LABEL}. "
            "Record firm, fee, and appointment status only — engagement scope belongs in the brief "
            "and filed engagement letters, not in this register. "
            "Missing appointment evidence stays Assumption / Not evidenced until engagement letters "
            "or fee proposals are filed."
        )
    else:
        intro = (
            f"Appointment register for {lead} engagement and taxonomy-expected disciplines. "
            f"The {lead} row is the design lead; coordination duties sit under that appointment. "
            "Record firm, fee, and appointment status only — engagement scope belongs in the brief "
            "and filed engagement letters, not in this register. "
            "Missing appointment evidence stays Assumption / Not evidenced until engagement letters "
            "or fee proposals are filed."
        )

    return "\n".join(
        [
            f"## {heading_for_section_id('consultants', work_type=context.work_type)}",
            "",
            intro,
            _emphasis_note(project, "consultants"),
            "",
            "\n".join(rows),
        ]
    )


def _render_taxonomy_citation_key(
    project: Project,
    pack: MobilisationEvidencePack | None = None,
    *,
    version: int = 1,
    citation_index: CitationIndex | None = None,
) -> str:
    del pack  # reserved for grounded status; citation list is document-only
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    index = citation_index or build_citation_index([])
    if index.documents:
        doc_block = "\n".join(format_citation_key_lines(index))
    else:
        doc_block = (
            "- No project evidence documents are cited yet. Upload brief, engagement, "
            "approvals, programme, and cost records to populate numbered citations that "
            "match the inline `[n]` markers used in the body sections above."
        )
    return "\n".join(
        [
            f"## {heading_for_section_id('citation-key', work_type=context.work_type)}",
            "",
            "Numbered project documents cited in this PMP. Each `[n]` marker in the body "
            "refers to the matching entry in the list below.",
            "",
            doc_block,
            "",
            f"Document control: draft v{version:02d}, review-only. "
            "Inline `[n]` markers in the body share these numbers. "
            "Supersede under `00-brief-pmp/` when new evidence arrives.",
        ]
    )


def _render_taxonomy_compliance(
    project: Project, seed_section_refs: dict[str, tuple[str, ...]] | None
) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    refs = (
        seed_section_refs.get("compliance-approvals", ()) if seed_section_refs else ()
    )
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
    ref_line = (
        f"Loaded seed sections: {', '.join(refs)}."
        if refs
        else "Loaded seed sections: TBC."
    )
    emphasis = _emphasis_note(project, "compliance-approvals")
    depth = ""
    if _top_weighted_section_id(project) == "compliance-approvals":
        depth = (
            f"Planning emphasis for this {context.building_class} {context.work_type or 'project'}: "
            "confirm the authority pathway, certifier engagement, inspection hold points, "
            "essential safety measures, and any live-environment or operational constraints that "
            "change lodgement sequencing. Keep seed-backed references visible and mark missing "
            "approval evidence as Not evidenced rather than inventing pathway detail."
        )
    return "\n".join(
        [
            f"## {heading_for_section_id('compliance-approvals', work_type=context.work_type)}",
            "",
            ref_line,
            "Do not use generic compliance prose where a required seed section is absent; mark the gap for user confirmation.",
            "The approval pathway, certifier position, authority inputs, and inspection or "
            "commissioning hold points are **Not evidenced** until the current corpus "
            "contains approval records, consultant advice, or authority correspondence.",
            depth,
            emphasis,
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
            "| Milestone | Status | Basis | Next action |",
            "| --- | --- | --- | --- |",
            "| Setup / brief confirmation | Active | Current project profile | Confirm scope and budget lock |",
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
    risk_text = (
        "; ".join(flag.title for flag in context.risk_flags)
        or "No derived uplift flags"
    )
    return "\n".join(
        [
            f"## {heading_for_section_id('cost-budget', work_type=context.work_type)}",
            "",
            f"Budget: {_metadata_value(budget)}.",
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
            "| Procurement route | Current | Confirm contract and tender pathway |",
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
    rows = [
        "| Risk | Owner | Status | Next action | Due |",
        "| --- | --- | --- | --- | --- |",
    ]
    for risk, owner, status, action, due in _taxonomy_risk_rows(project):
        rows.append(f"| {risk} | {owner} | {status} | {action} | {due} |")
    trailer = [
        "Primary risk register is capped at 8 rows; detail belongs in a companion annexure.",
    ]
    if _top_weighted_section_id(project) == "risks":
        trailer.append(
            "Risk status is conservative in scaffold mode: complexity options create rows, "
            "but severity and mitigation need recalibration when consultant advice, authority "
            "records, or cost evidence arrive."
        )
    return "\n".join(
        [
            f"## {heading_for_section_id('risks', work_type=context.work_type)}",
            "",
            "\n".join(rows),
            "",
            *trailer,
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
    lead = design_lead_discipline(context.work_type, context.work_scope)
    owner = "TBC" if lead == DESIGN_LEAD_UNCONFIRMED else lead
    actions = [
        "| Item | Owner | Status | Next |",
        "| --- | --- | --- | --- |",
        "| Scope boundary | Owner | Assumption | Lock brief |",
        f"| Approval pathway | {owner} | Assumption | Certifier |",
        "| Budget basis | Owner | Assumption | Cost evidence |",
        f"| Consultant roster | {owner} | Assumption | Appoint |",
    ]
    emphasis = _emphasis_note(project, "actions-decisions")
    depth = ""
    if _top_weighted_section_id(project) == "actions-decisions":
        depth = (
            "Decision blocks below are placeholders for the user to lock the PMP basis. "
            "Locked decisions should survive refreshes; conflicting uploaded evidence should "
            "create a visible action rather than silently changing the taxonomy or section "
            "weighting. For advisory work, prioritise reliance limits, evidence requests, "
            "and deliverable acceptance gates before expanding the physical works brief."
        )
    return "\n".join(
        [
            f"## {heading_for_section_id('actions-decisions', work_type=context.work_type)}",
            "",
            "\n".join(actions),
            "",
            depth,
            emphasis,
            "",
            _decision_block(
                "scope-boundary",
                "Scope boundary",
                "Confirm the scope boundary and exclusions.",
            ),
            "",
            _decision_block(
                "approval-pathway",
                "Approval pathway",
                "Confirm the approval and certification pathway.",
            ),
            "",
            _decision_block(
                "budget-basis",
                "Budget basis",
                "Confirm the budget, contingency, and cost-plan basis.",
            ),
            "",
            _decision_block(
                "consultant-roster",
                "Consultant roster",
                "Confirm the required consultant roster.",
            ),
        ]
    )


def _render_taxonomy_platform_scaffold(
    project: Project,
    pack: MobilisationEvidencePack | None = None,
    *,
    version: int = 1,
    seed_section_refs: dict[str, tuple[str, ...]] | None = None,
    citation_index: CitationIndex | None = None,
) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        raise ValueError("taxonomy scaffold requires building_class")
    pack = pack or MobilisationEvidencePack()
    index = citation_index or _citation_index_from_pack(pack)
    # Only render what this project needs. A plant replacement with no finishes
    # to schedule and an advisory engagement with nothing to procure used to
    # carry those sections as empty stubs.
    renderers = {
        "snapshot": lambda: _render_taxonomy_snapshot(project, citation_index=index),
        "scope-client-requirements": lambda: _render_taxonomy_scope(project),
        "consultants": lambda: _render_taxonomy_consultants(
            project, pack, citation_index=index
        ),
        "ffe-schedule": lambda: _render_taxonomy_ffe_schedule(project),
        "compliance-approvals": lambda: _render_taxonomy_compliance(
            project, seed_section_refs
        ),
        "programme": lambda: _render_taxonomy_programme(project),
        "cost-budget": lambda: _render_taxonomy_cost(project),
        "procurement-delivery": lambda: _render_taxonomy_procurement(project),
        "risks": lambda: _render_taxonomy_risks(project),
        "actions-decisions": lambda: _render_taxonomy_actions(project),
        "citation-key": lambda: _render_taxonomy_citation_key(
            project, pack, version=version, citation_index=index
        ),
    }
    applicable = context.sections or tuple(renderers)
    sections = [
        renderers[section_id]() for section_id in applicable if section_id in renderers
    ]
    rendered_headings = {
        line.strip()[3:].strip().lower()
        for section in sections
        for line in section.splitlines()
        if line.strip().startswith("## ")
    }
    missing = [
        heading
        for heading in pmp_section_headings(
            work_type=context.work_type, sections=applicable
        )
        if heading.lower() not in rendered_headings
    ]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"PMP scaffold missing required sections: {joined}")
    title = document_title(project=project)
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
            pack,
            version=version,
            seed_section_refs=seed_section_refs,
        )

    if draft_mode != "evidence_grounded":
        msg = f"PMP scaffold renderer supports evidence_grounded mode only (got {draft_mode!r})"
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
        _render_programme(pack),
        _render_cost_procurement(pack),
        _render_consultant_coordination(pack),
        _render_risks_skeleton(project, pack),
        _render_internal_audit(pack),
    ]

    headings = required_section_headings(project=project)
    rendered_headings = {
        line.strip()[3:].strip().lower()
        for section in sections
        for line in section.splitlines()
        if line.strip().startswith("## ")
    }
    missing = [
        heading for heading in headings if heading.lower() not in rendered_headings
    ]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"PMP scaffold missing required sections: {joined}")

    title = document_title(project=project)
    body = "\n\n".join(sections)
    return f"# {title}\n\n{body}\n"
