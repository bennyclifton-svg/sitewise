"""Deterministic cost plan scaffold rendering from a CostPlanEvidencePack."""

from __future__ import annotations

from typing import Literal

from app.database.project import Project
from app.sitewise.cost_plan_evidence import CostPlanEvidencePack, OwnerSuppliedItem
from app.sitewise.cost_plan_sources import document_title_for_role, required_section_headings
from app.sitewise.mobilisation_evidence import (
    GAP_CERTIFIER,
    GAP_GEOTECHNICAL,
    GAP_MASTER_PROGRAMME,
    FeeStage,
    pack_has_gap,
)

DraftMode = Literal["evidence_grounded", "platform_seeded"]

NARRATIVE_PLACEHOLDER = "[Pending cost plan narrative generation]"

_FEE_ROWS: tuple[tuple[str, str], ...] = (
    ("2", "DA and CC authority fees"),
    ("3", "BASIX certificate fee"),
    ("4", "Sydney Water / infrastructure"),
    ("5", "Levies and statutory"),
)

_CONSULTANT_ROWS: tuple[tuple[str, str], ...] = (
    ("6", "Structural engineer"),
    ("7", "Geotechnical engineer"),
    ("8", "Surveyor"),
    ("9", "Hydraulic / wastewater"),
    ("10", "BASIX / energy assessor"),
    ("11", "Principal certifier"),
)

_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("12", "Preliminaries"),
    ("13", "Siteworks and demolition"),
    ("14", "Footings and slab"),
    ("15", "Framing and roof"),
    ("16", "External envelope and lockup"),
    ("17", "Internal linings and joinery"),
    ("18", "Kitchen and bathrooms"),
    ("19", "Building services"),
    ("20", "Finishes and external works"),
)

# Practice-benchmark elemental split (Assumption — not market-rate advice).
# Labels MUST match _CONSTRUCTION_ROWS; integer percents sum to 100.
_CONSTRUCTION_BENCHMARK_PCT: tuple[tuple[str, int], ...] = (
    ("Preliminaries", 8),
    ("Siteworks and demolition", 7),
    ("Footings and slab", 12),
    ("Framing and roof", 18),
    ("External envelope and lockup", 15),
    ("Internal linings and joinery", 14),
    ("Kitchen and bathrooms", 9),
    ("Building services", 10),
    ("Finishes and external works", 7),
)

_PC_ALLOWANCE_ROWS: tuple[tuple[str, str], ...] = (
    ("21", "Kitchen joinery PC"),
    ("22", "Wet area / sanitary PC"),
    ("23", "Floor coverings PC"),
    ("24", "Lighting fittings PC"),
)

_CONTINGENCY_CODE = "25"

_STANDING_ASSUMPTIONS: tuple[str, ...] = (
    "Construction trade pricing TBC pending head-builder tender.",
    "Consultant fees (structural, geotechnical, survey, hydraulic, energy) TBC — not yet appointed.",
    "Authority and statutory fees (DA/CC, BASIX, Sydney Water, levies) TBC — benchmark only.",
    "PC allowance lines are placeholders until contract Schedule of Allowances.",
)

_RISK_SKELETON_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "Tender pricing vs owner brief ceiling",
        "High",
        "Owner",
        "Reconcile head-builder tender to owner brief construction ceiling",
        "TBC",
    ),
    (
        "Reactive soil / footing class unknown",
        "Medium–High",
        "Architect-PM",
        "Commission geotechnical report before slab pricing",
        "TBC",
    ),
    (
        "Planning pathway / DA programme slip",
        "High",
        "Owner",
        "Confirm DA pathway and September 2026 lodgement target",
        "TBC",
    ),
    (
        "Head-builder tender pricing volatility",
        "Medium",
        "Architect-PM",
        "Lock tender evaluation criteria before close",
        "TBC",
    ),
    (
        "Builder conflict / related-party tender",
        "Medium",
        "Architect-PM",
        "Declare Linden Constructions conflict before tender list lock",
        "TBC",
    ),
)


def _money(raw: str | None) -> str:
    if not raw:
        return "TBC"
    cleaned = raw.replace("$", "").replace(",", "").strip()
    if cleaned.isdigit():
        return f"${int(cleaned):,}"
    return raw if raw.startswith("$") else f"${raw}"


def _parse_amount(raw: str | None) -> int | None:
    if not raw:
        return None
    cleaned = raw.replace("$", "").replace(",", "").strip()
    return int(cleaned) if cleaned.isdigit() else None


def _inc_gst(ex_gst: int) -> int:
    return ex_gst * 11 // 10


def _ref_for_markers(refs: list[str], *markers: str) -> str:
    for ref in refs:
        path = ref.split("#", 1)[0].lower()
        if any(marker in path for marker in markers):
            return ref
    return "—"


def _owner_supplied_total_ex_gst(items: list[OwnerSuppliedItem]) -> int:
    total = 0
    for item in items:
        amount = _parse_amount(item.amount_ex_gst)
        if amount is not None:
            total += amount
    return total


def _known_indicative_total_ex_gst(pack: CostPlanEvidencePack) -> int | None:
    parts = [
        _parse_amount(pack.construction_budget_ceiling),
        _parse_amount(pack.contingency_amount),
        _parse_amount(pack.fee_total_ex_gst),
    ]
    owner_supplied = _owner_supplied_total_ex_gst(pack.owner_supplied_items)
    if not any(part is not None for part in parts) and owner_supplied == 0:
        return None
    return sum(part or 0 for part in parts) + owner_supplied


def _fee_stage_table(stages: list[FeeStage]) -> str:
    if not stages:
        return "| Stage | Trigger | Fee (ex GST) |\n| --- | --- | --- |\n| TBC | TBC | TBC |"
    rows = ["| Stage | Trigger | Fee (ex GST) |", "| --- | --- | --- |"]
    for stage in stages:
        rows.append(f"| {stage.stage} | {stage.trigger} | {_money(stage.fee_ex_gst)} |")
    return "\n".join(rows)


def _owner_supplied_lines(items: list[OwnerSuppliedItem]) -> list[str]:
    if not items:
        return ["- Owner-supplied items: **Assumption — not yet listed in evidence**."]
    lines: list[str] = ["- **Owner-supplied items (below contract sum):**"]
    for item in items:
        amount = _money(item.amount_ex_gst) if item.amount_ex_gst else "TBC"
        lines.append(f"  - {item.label}: {amount} (owner-supplied; GST basis not stated in brief)")
    total = _owner_supplied_total_ex_gst(items)
    if total:
        lines.append(f"  - **Owner-supplied subtotal:** ${total:,} (owner brief allowance; GST basis not stated).")
    return lines


def _render_project_name_location(project: Project, pack: CostPlanEvidencePack) -> str:
    name = pack.project_name or project.title
    site = pack.site_address or "**Assumption: site address not yet evidenced**"
    owners = pack.owners or "TBC"
    return "\n".join(
        [
            "## Project name and location",
            "",
            f"**Project:** {name}",
            f"**Site:** {site}",
            f"**Owners:** {owners}",
            f"**Archetype / role / state:** {project.archetype}, {project.user_role}, {project.state}",
        ]
    )


def _render_source_evidence(pack: CostPlanEvidencePack) -> str:
    mob = pack.mobilisation
    on_file: list[str] = []
    if mob.engagement_executed_date or mob.fee_total_ex_gst:
        on_file.append("architect engagement letter (executed)")
    if mob.fee_total_ex_gst:
        on_file.append("architect fee proposal")
    if pack.owner_brief_on_file:
        on_file.append("owner project brief (signed)")
    if pack.planning_memo_on_file:
        on_file.append("planning pathway memo")
    if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL):
        on_file.append("geotechnical report")
    if not pack_has_gap(pack.mobilisation, GAP_MASTER_PROGRAMME):
        on_file.append("master programme")
    if not pack_has_gap(pack.mobilisation, GAP_CERTIFIER):
        on_file.append("principal certifier appointment")

    evidence_line = ", ".join(on_file) if on_file else "project cost evidence indexed"
    refs = pack.evidence_refs
    engagement_ref = _ref_for_markers(refs, "engagement-letter", "engagement_letter")
    brief_ref = _ref_for_markers(
        refs,
        "owner-project-brief",
        "owner_project_brief",
        "owner-brief",
        "project-brief",
        "00-brief-pmp",
    )
    planning_ref = _ref_for_markers(refs, "planning-pathway", "planning_pathway", "09-planning")
    geotech_ref = _ref_for_markers(refs, "geotechnical", "geotech", "06-geotechnical")

    rows = [
        "| Section | Evidence status | Ref |",
        "| --- | --- | --- |",
        (
            "| Budget reconciliation | "
            f"{'Grounded' if pack.construction_budget_ceiling else 'Partial'} | "
            f"{brief_ref if pack.construction_budget_ceiling else '—'} |"
        ),
        (
            "| Architect fee / PM fee | Grounded | "
            f"{engagement_ref if engagement_ref != '—' else (refs[0] if refs else '—')} |"
        ),
        (
            "| Construction breakdown | "
            f"{'Partial' if pack.construction_budget_ceiling else 'Not evidenced'} | "
            f"{brief_ref if pack.construction_budget_ceiling else '—'} |"
        ),
        (
            "| Planning pathway | "
            f"{'Grounded' if pack.planning_pathway_summary else 'Partial'} | "
            f"{planning_ref if pack.planning_memo_on_file else '—'} |"
        ),
        (
            "| Geotechnical / footing class | "
            f"{'Grounded' if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL) else 'Not evidenced'} | "
            f"{geotech_ref if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL) else '—'} |"
        ),
    ]
    return "\n".join(
        [
            "## Source evidence used",
            "",
            f"**Evidence on file:** {evidence_line}.",
            "",
            *rows,
            "",
            "**Gaps:** "
            + (
                "; ".join(pack.gaps)
                if pack.gaps
                else "No mobilisation evidence gaps; construction trade pricing, consultant "
                "fees and authority charges remain unpriced (see Assumptions and exclusions)."
            ),
        ]
    )


def _render_budget_reconciliation(pack: CostPlanEvidencePack) -> str:
    mob = pack.mobilisation
    rows = [
        "| Figure | Source | Amount (ex GST) | GST basis | Status | Adopted? |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if pack.construction_budget_ceiling:
        signed = f" ({pack.owner_brief_signed_date})" if pack.owner_brief_signed_date else ""
        rows.append(
            "| Owner working construction ceiling | "
            f"Owner project brief{signed} | "
            f"{_money(pack.construction_budget_ceiling)} | ex GST | Evidenced | "
            "**Yes — cost-control reference (construction)** |"
        )
    else:
        rows.append(
            "| Owner working construction ceiling | Assumption | TBC | ex GST | Assumption | Qualified |"
        )
    if pack.contingency_amount:
        pct = f" ({pack.contingency_percent}%)" if pack.contingency_percent else ""
        rows.append(
            "| Owner contingency allowance | Owner project brief | "
            f"{_money(pack.contingency_amount)}{pct} | ex GST | Evidenced | "
            "Qualified — owner-held, outside contract sum until allocated |"
        )
    fee = _money(mob.fee_total_ex_gst)
    executed = mob.engagement_executed_date or "TBC"
    rows.append(
        f"| Architect fixed professional fee | Engagement letter executed {executed} | "
        f"{fee} | ex GST | Locked | Adopted (outside construction ceiling) |"
    )
    rows.append(
        "| Head construction contract | — | TBC | ex GST | Not tendered | — |"
    )
    return "\n".join(
        [
            "## Budget reconciliation and control decision",
            "",
            "Competing figures reconciled below. **Do not treat construction TBC lines as approved budget.**",
            "",
            *rows,
            "",
            (
                "**Cost-control reference (construction):** "
                f"{_money(pack.construction_budget_ceiling) if pack.construction_budget_ceiling else 'TBC — owner to confirm'}"
                " ex GST."
            ),
        ]
    )


def _render_total_budget(pack: CostPlanEvidencePack) -> str:
    construction = (
        _money(pack.construction_budget_ceiling)
        if pack.construction_budget_ceiling
        else "TBC (Assumption)"
    )
    fee = _money(pack.fee_total_ex_gst)
    status = "Indicative (owner brief on file)" if pack.construction_budget_ceiling else "Assumption"
    lines = [
        "## Total approved or indicative budget",
        "",
        f"- **Construction cost-control reference:** {construction} ex GST — {status}.",
        f"- **Architect / PM fixed fee (additional):** {fee} ex GST — locked per engagement letter.",
    ]
    if pack.contingency_amount:
        lines.append(
            f"- **Owner-held contingency (additional):** {_money(pack.contingency_amount)} ex GST — "
            "evidenced in owner brief; not part of construction ceiling."
        )
    if pack.owner_supplied_items:
        total = _owner_supplied_total_ex_gst(pack.owner_supplied_items)
        if total:
            lines.append(
                f"- **Owner-supplied allowances (additional):** ${total:,} — owner procurement outside "
                "builder contract (owner brief allowance; GST basis not stated)."
            )
    indicative = _known_indicative_total_ex_gst(pack)
    if indicative is not None:
        lines.append(
            f"- **Indicative total project cost (known buckets only):** ${indicative:,} ex GST — "
            "excludes authority fees, consultants, construction trade breakdown, and PC allowances "
            "until quoted or tendered."
        )
        lines.append(
            f"- **Indicative total inc GST (owner-facing reference):** ${_inc_gst(indicative):,} — "
            "translate ex-GST workbook figures for owner-occupier cash planning."
        )
    else:
        lines.append(
            "- **Total project cost:** Sum of construction reference + consultant/fees + authority + "
            "owner-supplied items — **not a single headline until tender and appointments are locked**."
        )
    return "\n".join(lines)


def _render_gst_basis(pack: CostPlanEvidencePack) -> str:
    translations: list[str] = []
    fee_amount = _parse_amount(pack.fee_total_ex_gst)
    if fee_amount is not None:
        translations.append(f"Architect fee inc GST: ${_inc_gst(fee_amount):,}.")
    ceiling_amount = _parse_amount(pack.construction_budget_ceiling)
    if ceiling_amount is not None:
        translations.append(f"Construction ceiling inc GST: ${_inc_gst(ceiling_amount):,}.")
    contingency_amount = _parse_amount(pack.contingency_amount)
    if contingency_amount is not None:
        translations.append(f"Owner contingency inc GST: ${_inc_gst(contingency_amount):,}.")

    lines = [
        "## GST basis",
        "",
        "**All workbook figures in this cost plan exclude GST** (Create Cost Plan v1 default).",
        "Owners often think in inc-GST terms for residential projects — translate where helpful.",
    ]
    if translations:
        lines.append("**Owner-facing inc-GST reference (evidenced amounts):** " + " ".join(translations))
    return "\n".join(lines)


def _render_cost_breakdown(pack: CostPlanEvidencePack) -> str:
    mob = pack.mobilisation
    fee = _money(mob.fee_total_ex_gst)
    fee_subtotal = fee if fee != "TBC" else "TBC"
    contingency = _money(pack.contingency_amount) if pack.contingency_amount else "TBC"
    pct = pack.contingency_percent or "5–10"
    cont_status = "Evidenced" if pack.contingency_amount else "Assumption"
    cont_basis = (
        f"{pct}% owner-held (owner brief)"
        if pack.contingency_amount
        else f"{pct}% construction (benchmark)"
    )

    rows = [
        "| Cost Code | Category | Cost Items | Budget | Status | Basis |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| 1 | Fees and charges | HCS architect / PM fee | {fee} | Approved | Engagement letter |",
    ]
    for code, label in _FEE_ROWS:
        rows.append(
            f"| {code} | Fees and charges | {label} | TBC | Assumption | Benchmark |"
        )
    for code, label in _CONSULTANT_ROWS:
        if label == "Principal certifier" and not pack_has_gap(pack.mobilisation, GAP_CERTIFIER):
            fee = _money(pack.certifier_fee_ex_gst) if pack.certifier_fee_ex_gst else "Owner-direct"
            name = pack.certifier_name or "appointed"
            rows.append(
                f"| {code} | Consultants | {label} | {fee} | Grounded | "
                f"Appointed ({name}); owner-direct fee |"
            )
            continue
        rows.append(
            f"| {code} | Consultants | {label} | TBC | Assumption | Not yet appointed |"
        )
    ceiling = _parse_amount(pack.construction_budget_ceiling)
    if ceiling is not None:
        pct_by_label = dict(_CONSTRUCTION_BENCHMARK_PCT)
        running = 0
        last_index = len(_CONSTRUCTION_ROWS) - 1
        for index, (code, label) in enumerate(_CONSTRUCTION_ROWS):
            if index == last_index:
                amount = ceiling - running
            else:
                amount = round(ceiling * pct_by_label[label] / 100)
                running += amount
            rows.append(
                f"| {code} | Construction | {label} | ${amount:,} | Assumption | "
                f"Benchmark % of ceiling |"
            )
        construction_subtotal = f"${ceiling:,}"
    else:
        for code, label in _CONSTRUCTION_ROWS:
            rows.append(
                f"| {code} | Construction | {label} | TBC | Assumption | Pending head-builder tender |"
            )
        construction_subtotal = "TBC"
    for code, label in _PC_ALLOWANCE_ROWS:
        rows.append(
            f"| {code} | PC allowances | {label} | TBC | Assumption | Selection pending — contract PC schedule |"
        )
    rows.append(
        f"| {_CONTINGENCY_CODE} | Contingency / allowances | Owner-held contingency | {contingency} | "
        f"{cont_status} | {cont_basis} |"
    )

    # The grounded certifier fee is owner-direct (outside the builder contract), so it is
    # intentionally excluded from the Consultants subtotal and the grand total — same
    # treatment as owner-supplied items. Consultants subtotal stays TBC until appointments.
    subtotal_amounts = [
        _parse_amount(fee_subtotal),
        _parse_amount(construction_subtotal),
        _parse_amount(contingency),
    ]
    itemised_total = sum(amount for amount in subtotal_amounts if amount is not None)
    grand_total = f"${itemised_total:,}" if itemised_total else "TBC"
    grand_basis = "Sum of itemised subtotals — construction is benchmark % of ceiling, consultants/PC TBC"
    rows.extend(
        [
            f"| | | **Subtotal — Fees and charges** | {fee_subtotal} | | |",
            "| | | **Subtotal — Consultants** | TBC | | |",
            f"| | | **Subtotal — Construction** | {construction_subtotal} | | |",
            "| | | **Subtotal — PC allowances** | TBC | | |",
            f"| | | **Subtotal — Contingency / allowances** | {contingency} | | |",
            f"| | | **Grand total (ex GST)** | {grand_total} | Assumption | {grand_basis} |",
        ]
    )
    owner_lines = _owner_supplied_lines(pack.owner_supplied_items)
    return "\n".join(
        [
            "## Cost breakdown by category",
            "",
            "Workbook-ready groups: Fees and charges → Consultants → Construction → PC allowances → "
            "Contingency / allowances.",
            "Construction rows follow NSW residential taxonomy.",
            "Construction rows are an indicative benchmark split of the owner ceiling (Assumption) "
            "until head-builder tender returns a priced schedule.",
            "",
            *rows,
            "",
            *owner_lines,
        ]
    )


def _render_locked_appointments(pack: CostPlanEvidencePack) -> str:
    mob = pack.mobilisation
    executed = mob.engagement_executed_date or "TBC"
    fee = _money(mob.fee_total_ex_gst)
    rows = [
        "## Known locked contract and appointment values",
        "",
        "| Supplier | Scope | Amount (ex GST) | Date | Evidence |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| {mob.appointee or 'Harrison Clarke Studio Pty Ltd'} | Architect / PM | "
            f"{fee} | {executed} | Engagement letter |"
        ),
    ]
    if pack.certifier_name and not pack_has_gap(pack.mobilisation, GAP_CERTIFIER):
        cert_fee = _money(pack.certifier_fee_ex_gst) if pack.certifier_fee_ex_gst else "Owner-direct"
        rows.append(
            f"| {pack.certifier_name} | Principal certifier | {cert_fee} | Appointed | "
            "Certifier appointment |"
        )
    rows.extend(
        [
            "",
            "All other consultant and construction appointments: **Assumption — not yet locked**.",
        ]
    )
    return "\n".join(rows)


def _render_allowances_contingency(pack: CostPlanEvidencePack) -> str:
    lines = [
        "## Allowances and contingency",
        "",
    ]
    if pack.contingency_amount:
        pct = f" ({pack.contingency_percent}%)" if pack.contingency_percent else ""
        lines.append(
            f"- **Owner-held construction contingency:** {_money(pack.contingency_amount)}{pct} ex GST per "
            "owner brief (reactive/sloping site allowance). Held outside the construction ceiling until "
            "allocated — not available scope money."
        )
    else:
        lines.append("- **Construction contingency:** TBC — typically 5–10% on construction only (Assumption).")
    lines.append(
        "- **PC allowances:** Kitchen, wet area, floor coverings, and lighting PC lines are placeholders "
        "until head-builder tender or contract Schedule of Allowances is locked."
    )
    if pack.owner_supplied_items:
        lines.append("- **Owner-supplied allowances:**")
        for item in pack.owner_supplied_items:
            amount = _money(item.amount_ex_gst) if item.amount_ex_gst else "TBC"
            lines.append(f"  - {item.label}: {amount} (owner-supplied; GST basis not stated)")
    lines.append("- Do not use contingency to absorb unresolved scope without labelling.")
    return "\n".join(lines)


def _render_pm_fee_treatment(pack: CostPlanEvidencePack) -> str:
    mob = pack.mobilisation
    fee = _money(mob.fee_total_ex_gst)
    return "\n".join(
        [
            "## PM fee treatment",
            "",
            f"Architect-PM fixed fee **{fee} ex GST** is **outside** the owner working construction ceiling "
            f"({_money(pack.construction_budget_ceiling) if pack.construction_budget_ceiling else 'TBC'}).",
            "Staged triggers per engagement letter:",
            "",
            _fee_stage_table(mob.fee_stages),
            "",
            f"Construction administration assumed for {mob.ca_months_assumed or 12} months after head contract.",
        ]
    )


def _render_assumptions_exclusions(pack: CostPlanEvidencePack) -> str:
    items = [
        "- Construction line items remain benchmark/TBC until head-builder tender returns priced schedule.",
        "- Authority fees and specialist consultants not yet appointed or quoted.",
        "- PC allowance rows are placeholders until contract Schedule of Allowances is agreed at tender.",
    ]
    if not pack.construction_budget_ceiling:
        items.append("- Owner working construction ceiling not evidenced — confirm before cost-control lock.")
    if pack.construction_budget_ceiling and pack.contingency_amount:
        items.append(
            "- Owner-held contingency is evidenced separately from the construction ceiling — do not double-count."
        )
    items.extend(f"- Assumption: {gap}." for gap in pack.gaps)
    return "\n".join(["## Assumptions and exclusions", "", *items])


def _render_risks_skeleton(pack: CostPlanEvidencePack) -> str:
    rows = ["| Risk | Impact | Owner | Next action | Due |", "| --- | --- | --- | --- | --- |"]
    for risk, impact, owner, action, due in _RISK_SKELETON_ROWS:
        if (
            pack.construction_budget_ceiling
            and risk == "Tender pricing vs owner brief ceiling"
        ):
            action = (
                f"Reconcile tender pricing to {_money(pack.construction_budget_ceiling)} ex GST ceiling"
            )
        if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL) and risk.startswith(
            "Reactive soil"
        ):
            action = "Adopt geotechnical findings in footing/slab allowance before tender"
            impact = "Medium"
        rows.append(f"| {risk} | {impact} | {owner} | {action} | {due} |")
    return "\n".join(
        [
            "## Risks and review questions",
            "",
            *rows,
            "",
            f"Risk review questions and due dates: {NARRATIVE_PLACEHOLDER}",
        ]
    )


def _render_authority_gates(pack: CostPlanEvidencePack) -> str:
    pathway = pack.planning_pathway_summary or pack.mobilisation.planning_pathway or "DA pathway — confirm"
    geotech_status = (
        "Grounded — adopt H1 (or as reported) in slab pricing"
        if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL)
        else "Assumption"
    )
    geotech_action = (
        "Issue footing/slab allowance note to tender package"
        if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL)
        else "Commission if absent"
    )
    certifier_status = (
        "Grounded — principal certifier appointed"
        if not pack_has_gap(pack.mobilisation, GAP_CERTIFIER)
        else "Assumption"
    )
    certifier_action = (
        "Coordinate DA/CC pathway with appointed certifier"
        if not pack_has_gap(pack.mobilisation, GAP_CERTIFIER)
        else (
            "Appoint after DA determination (confirm CC pathway with certifier at schematic)"
            if pack.planning_pathway_summary
            else "Appoint after DA determination"
        )
    )
    return "\n".join(
        [
            "## Authority, compliance and procurement gates",
            "",
            "| Gate | Status | Cost impact | Next action |",
            "| --- | --- | --- | --- |",
            f"| Planning pathway | {pathway} | High if wrong | Owner decision recorded |",
            f"| Geotechnical / footing class | {geotech_status} | Medium–High | {geotech_action} |",
            "| HBCF / HOW / licence | Assumption | Statutory | Verify before head contract |",
            f"| Principal certifier | {certifier_status} | Programme | {certifier_action} |",
            "| Head-builder procurement | Partial | High | Tender after DD/IFC package |",
        ]
    )


def _render_recommended_next_steps() -> str:
    return "\n".join(
        [
            "## Recommended next steps",
            "",
            f"1. {NARRATIVE_PLACEHOLDER}",
        ]
    )


def _render_internal_audit(pack: CostPlanEvidencePack) -> str:
    mob = pack.mobilisation
    facts = [
        f"Owners {pack.owners or 'TBC'}; site {pack.site_address or 'TBC'}.",
        (
            f"HCS architect-PM engaged; fee {_money(mob.fee_total_ex_gst)} ex GST; "
            f"executed {mob.engagement_executed_date or 'TBC'}."
        ),
    ]
    if pack.construction_budget_ceiling:
        facts.append(
            f"Owner working construction ceiling {_money(pack.construction_budget_ceiling)} ex GST "
            f"(owner brief{(' signed ' + pack.owner_brief_signed_date) if pack.owner_brief_signed_date else ''})."
        )
    if pack.contingency_amount:
        facts.append(
            f"Owner contingency {_money(pack.contingency_amount)} ex GST"
            f"{(' (' + pack.contingency_percent + '%)') if pack.contingency_percent else ''}."
        )
    if pack.owner_supplied_items:
        total = _owner_supplied_total_ex_gst(pack.owner_supplied_items)
        if total:
            facts.append(f"Owner-supplied allowances total ${total:,} per owner brief (GST basis not stated).")
    if pack.planning_pathway_summary:
        facts.append(f"Planning pathway: {pack.planning_pathway_summary}.")
    if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL):
        facts.append("Geotechnical investigation report on file.")
    if not pack_has_gap(pack.mobilisation, GAP_MASTER_PROGRAMME):
        facts.append("Master programme on file.")
    if not pack_has_gap(pack.mobilisation, GAP_CERTIFIER):
        facts.append("Principal certifier appointed.")
    if mob.target_da_lodgement:
        facts.append(f"Target DA lodgement {mob.target_da_lodgement} per engagement letter.")

    assumptions = [f"Assumption: {gap}." for gap in pack.gaps]
    assumptions.extend(f"Assumption: {item}" for item in _STANDING_ASSUMPTIONS)
    return "\n".join(
        [
            "## Internal audit layer",
            "",
            "- **Facts**",
            *[f"  - {fact}" for fact in facts[:8]],
            "- **Assumptions**",
            *[f"  - {item}" for item in assumptions],
            "- **Judgements**",
            f"  - {NARRATIVE_PLACEHOLDER}",
            "- **Recommendations**",
            f"  - {NARRATIVE_PLACEHOLDER}",
            "- **Cost evidence conflicts**",
            "  - None identified — construction breakdown pending tender.",
        ]
    )


def render_cost_plan_scaffold(
    project: Project,
    pack: CostPlanEvidencePack,
    draft_mode: DraftMode,
) -> str:
    """Render deterministic cost plan markdown scaffold from project overlays and evidence pack."""
    if draft_mode != "evidence_grounded":
        msg = f"Cost plan scaffold renderer supports evidence_grounded mode only (got {draft_mode!r})"
        raise ValueError(msg)

    user_role = project.user_role or "architect-pm"
    if user_role != "architect-pm":
        msg = f"Cost plan scaffold renderer supports architect-pm role only (got {user_role!r})"
        raise ValueError(msg)

    sections = [
        _render_project_name_location(project, pack),
        _render_source_evidence(pack),
        _render_budget_reconciliation(pack),
        _render_total_budget(pack),
        _render_gst_basis(pack),
        _render_cost_breakdown(pack),
        _render_locked_appointments(pack),
        _render_allowances_contingency(pack),
        _render_pm_fee_treatment(pack),
        _render_assumptions_exclusions(pack),
        _render_risks_skeleton(pack),
        _render_authority_gates(pack),
        _render_recommended_next_steps(),
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
        raise RuntimeError(f"Cost plan scaffold missing required sections: {joined}")

    title = document_title_for_role(user_role)
    body = "\n\n".join(sections)
    return f"# {title}\n\n{body}\n"
