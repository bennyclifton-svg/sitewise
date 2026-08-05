"""Deterministic cost plan scaffold rendering from a CostPlanEvidencePack."""

from __future__ import annotations

from typing import Literal

from app.database.project import Project
from app.sitewise.cost_plan_coverage import coverage_spec
from app.sitewise.cost_plan_evidence import CostPlanEvidencePack, OwnerSuppliedItem
from app.sitewise.cost_plan_lines import (
    _CONSTRUCTION_BENCHMARK_PCT_BY_FAMILY,
    _PC_ALLOWANCE_ROWS_BY_FAMILY,
    CostPlanLine,
    _appointee_label,
    _coverage_family,
    _money,
    _no_rate_pack_disclosure,
    _parse_amount,
    cost_plan_lines,
)
from app.sitewise.cost_plan_sources import document_title, required_section_headings
from app.sitewise.mobilisation_evidence import (
    GAP_CERTIFIER,
    GAP_GEOTECHNICAL,
    GAP_MASTER_PROGRAMME,
    FeeStage,
    pack_has_gap,
)
from app.sitewise.pmp_citations import (
    CitationIndex,
    build_citation_index,
    format_citation_key_lines,
)

DraftMode = Literal["evidence_grounded", "platform_seeded"]

NARRATIVE_PLACEHOLDER = "[Pending cost plan narrative generation]"


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


def _received_proposal(pack: CostPlanEvidencePack, kind: str):
    return next(
        (proposal for proposal in pack.received_cost_proposals if proposal.kind == kind),
        None,
    )


def _received_main_works_proposal(pack: CostPlanEvidencePack):
    return _received_proposal(pack, "main_works")


def _received_architecture_proposal(pack: CostPlanEvidencePack):
    return _received_proposal(pack, "architecture")


def _known_indicative_total_ex_gst(pack: CostPlanEvidencePack) -> int | None:
    if pack.reconciled_items:
        proposal_total = sum(
            int(item.budget or 0) for item in pack.reconciled_items
        )
        contingency = _parse_amount(pack.contingency_amount) or 0
        return proposal_total + contingency

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


def _builder_rom_amount(pack: CostPlanEvidencePack) -> str:
    rom = pack.mobilisation.builder_rom
    if not rom:
        return "TBC"
    for separator in (" — ", " - ", " â€” "):
        if separator in rom:
            return rom.split(separator, 1)[1].rstrip(".")
    return rom.rstrip(".")


def _project_profile_label(project: Project) -> str:
    building_class = project.building_class
    work_type = project.work_type
    if building_class and work_type:
        profile = f"{building_class} / {work_type}"
    else:
        profile = building_class or project.archetype or "TBC"
    return f"{profile}, {project.state or 'TBC'}"


def _evidence_path(ref: str) -> str:
    path = ref.split(":", 1)[-1].split("#", 1)[0]
    return path.replace("\\", "/")


def _citation_index(pack: CostPlanEvidencePack) -> CitationIndex:
    return build_citation_index([(_evidence_path(ref), "on file") for ref in pack.evidence_refs])


def _citation_for_markers(
    pack: CostPlanEvidencePack, citations: CitationIndex, *markers: str
) -> str:
    ref = _ref_for_markers(pack.evidence_refs, *markers)
    return citations.token_for(_evidence_path(ref)) if ref != "—" else "—"


def _body(rendered_section: str) -> str:
    return rendered_section.split("\n", 1)[1].lstrip() if "\n" in rendered_section else ""


def _cost_breakdown_table(project: Project, pack: CostPlanEvidencePack) -> str:
    lines = _render_cost_breakdown(project, pack).splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.startswith("| Cost Code |")
    )
    return "\n".join(lines[start:])


def _render_summary(
    project: Project, pack: CostPlanEvidencePack, citations: CitationIndex
) -> str:
    brief = _citation_for_markers(
        pack,
        citations,
        "owner-project-brief",
        "owner_project_brief",
        "owner-brief",
        "project-brief",
        "00-brief-pmp",
    )
    engagement = _citation_for_markers(
        pack, citations, "engagement-letter", "engagement_letter", "fee-proposal"
    )
    main_works = _received_main_works_proposal(pack)
    architecture = _received_architecture_proposal(pack)
    lines = [
        "## Cost plan summary and control decision",
        "",
        f"**Project:** {pack.project_name or project.title} — {pack.site_address or 'site not evidenced'}.",
        f"**Owners:** {pack.owners or 'TBC'}.",
        f"**Profile:** {_project_profile_label(project)}. All figures below are ex GST.",
    ]
    if pack.construction_budget_ceiling:
        lines.append(
            f"**Construction cost-control reference:** {_money(pack.construction_budget_ceiling)} {brief}."
        )
    elif main_works:
        main_works_ref = citations.token_for(_evidence_path(main_works.evidence_ref))
        lines.append(
            f"**Received main-works proposal:** {_money(main_works.total_ex_gst)} "
            f"{main_works_ref}; proposal on file, not an accepted contract."
        )
    else:
        lines.append(
            "**Construction cost-control reference:** TBC — no owner brief or priced proposal on file."
        )
    architect_fee = pack.fee_total_ex_gst or (
        architecture.total_ex_gst if architecture else None
    )
    architect_status = (
        "proposed and additional to construction."
        if architecture and not pack.fee_total_ex_gst
        else "additional to the construction ceiling."
    )
    lines.append(
        f"**Architect / PM fee:** {_money(architect_fee)} {engagement}; {architect_status}"
    )
    if pack.contingency_amount:
        lines.append(
            f"**Owner-held contingency:** {_money(pack.contingency_amount)} "
            f"({pack.contingency_percent or 'TBC'}%) {brief}; do not treat it as scope money."
        )
    indicative_total = _known_indicative_total_ex_gst(pack)
    if indicative_total is not None:
        lines.append(
            f"**Indicative total project cost (known buckets):** ${indicative_total:,} ex GST "
            f"/ ${_inc_gst(indicative_total):,} inc GST."
        )
    lines.append(
        "**Decision:** reconcile tendered construction pricing to the control reference before any scope or contingency drawdown."
    )
    return "\n".join(lines)


def _render_budget_and_breakdown(
    project: Project, pack: CostPlanEvidencePack, citations: CitationIndex
) -> str:
    brief = _citation_for_markers(
        pack, citations, "owner-project-brief", "owner_project_brief", "owner-brief", "project-brief", "00-brief-pmp"
    )
    engagement = _citation_for_markers(
        pack, citations, "engagement-letter", "engagement_letter", "fee-proposal"
    )
    main_works = _received_main_works_proposal(pack)
    architecture = _received_architecture_proposal(pack)
    rows = [
        "| Figure | Amount (ex GST) | Control treatment | Ref |",
        "| --- | --- | --- | --- |",
        (
            f"| Construction ceiling | {_money(pack.construction_budget_ceiling)} | Cost-control reference | {brief} |"
            if pack.construction_budget_ceiling
            else "| Construction ceiling | TBC | Owner control reference not supplied | — |"
        ),
        (
            f"| Received main-works proposal | {_money(main_works.total_ex_gst)} | Proposal on file, not accepted or committed | "
            f"{citations.token_for(_evidence_path(main_works.evidence_ref))} |"
            if main_works
            else "| Received main-works proposal | TBC | No fixed-price proposal on file | — |"
        ),
        (
            f"| Architect / PM fee | {_money(pack.fee_total_ex_gst or (architecture.total_ex_gst if architecture else None))} | "
            f"{'Proposal on file, not committed' if architecture and not pack.fee_total_ex_gst else 'Additional to construction'} | {engagement} |"
        ),
        (
            f"| Owner contingency | {_money(pack.contingency_amount)} | Owner-held, outside contract sum | {brief} |"
            if pack.contingency_amount
            else "| Owner contingency | TBC | Assumption | — |"
        ),
        "| Head contract | TBC | Not tendered | — |",
    ]
    family = _coverage_family(project)
    breakdown_intro = (
        "Construction rows are mapped from the received fixed-price main-works proposal; "
        "they remain proposed until the contract is accepted."
        if main_works
        else (
            "Construction rows are an indicative benchmark split until a tendered "
            "trade schedule is available."
            if family == "residential_class1_new"
            else _no_rate_pack_disclosure(family)
        )
    )
    return "\n".join(
        [
            "## Budget reconciliation and cost breakdown",
            "",
            *rows,
            "",
            "### Cost breakdown",
            breakdown_intro,
            "",
            _cost_breakdown_table(project, pack),
        ]
    )


def _render_commitments_allowances(
    project: Project, pack: CostPlanEvidencePack, citations: CitationIndex
) -> str:
    engagement = _citation_for_markers(
        pack, citations, "engagement-letter", "engagement_letter", "fee-proposal"
    )
    main_works = _received_main_works_proposal(pack)
    architecture = _received_architecture_proposal(pack)
    brief = _citation_for_markers(
        pack, citations, "owner-project-brief", "owner_project_brief", "owner-brief", "project-brief", "00-brief-pmp"
    )
    rows = [
        "| Commitment / allowance | Amount (ex GST) | Status | Ref |",
        "| --- | --- | --- | --- |",
        f"| {_appointee_label(pack)} architect / PM | {_money(pack.fee_total_ex_gst or (architecture.total_ex_gst if architecture else None))} | "
        f"{'Proposed' if architecture and not pack.fee_total_ex_gst else 'Locked'} | {engagement} |",
    ]
    if pack.certifier_name and not pack_has_gap(pack.mobilisation, GAP_CERTIFIER):
        rows.append(
            f"| {pack.certifier_name} principal certifier | {_money(pack.certifier_fee_ex_gst) if pack.certifier_fee_ex_gst else 'Owner-direct'} | Appointed | "
            f"{_citation_for_markers(pack, citations, 'certifier-appointment', '12-certifier')} |"
        )
    family = _coverage_family(project)
    construction_rows_note = (
        "- Construction rows map a received fixed-price proposal; they are not an accepted or committed contract."
        if main_works
        else (
            "- Construction rows are lump-sum TBC placeholders, not tendered prices."
            if coverage_spec(family).structure_only
            else "- Construction benchmark rows are assumptions, not tendered prices."
        )
    )
    lines = [
        "## Commitments, allowances and exclusions",
        "",
        *rows,
        "",
        f"- Contingency: {_money(pack.contingency_amount) if pack.contingency_amount else 'TBC'} {brief}.",
        (
            "- Client-direct / landlord interface allowances, authority fees and "
            "unappointed consultants remain TBC until allocation, tender or appointment."
            if family == "commercial_fitout"
            else (
                "- Client/owner-direct allowances, authority fees and unappointed "
                "consultants remain TBC until allocation, tender or appointment."
                if _PC_ALLOWANCE_ROWS_BY_FAMILY[family]
                else "- Authority fees and unappointed consultants remain TBC until tender or appointment."
            )
        ),
        construction_rows_note,
    ]
    if pack.owner_supplied_items:
        lines.append("- Owner-supplied items (outside builder contract): " + "; ".join(
            f"{item.label} {_money(item.amount_ex_gst) if item.amount_ex_gst else 'TBC'}"
            for item in pack.owner_supplied_items
        ) + ".")
    if pack.mobilisation.builder_rom:
        lines.append(
            f"- Builder ROM {_builder_rom_amount(pack)} is a market signal only, not a tender."
        )
    return "\n".join(lines)


def _render_risks_gates_actions(
    project: Project,
    pack: CostPlanEvidencePack,
) -> str:
    return "\n".join(
        [
            "## Risks, delivery gates and next actions",
            "",
            "### Risk register",
            NARRATIVE_PLACEHOLDER,
            "",
            "### Delivery gates",
            _body(_render_authority_gates(project, pack)),
            "",
            "### Next actions",
            NARRATIVE_PLACEHOLDER,
        ]
    )


def _render_sources_and_audit(pack: CostPlanEvidencePack, citations: CitationIndex) -> str:
    brief = _citation_for_markers(
        pack, citations, "owner-project-brief", "owner_project_brief", "owner-brief", "project-brief", "00-brief-pmp"
    )
    engagement = _citation_for_markers(
        pack, citations, "engagement-letter", "engagement_letter", "fee-proposal"
    )
    map_rows = [
        "| Cost-plan area | Evidence status | Ref |",
        "| --- | --- | --- |",
        f"| Cost-control reference | {'Grounded' if pack.construction_budget_ceiling else 'Not evidenced'} | {brief} |",
        f"| Architect / PM fee | Grounded | {engagement} |",
        f"| Construction breakdown | {'Partial' if pack.construction_budget_ceiling else 'Not evidenced'} | {brief} |",
    ]
    facts = [
        f"Construction control reference {_money(pack.construction_budget_ceiling) if pack.construction_budget_ceiling else 'TBC'} {brief}.",
        f"Architect / PM fee {_money(pack.fee_total_ex_gst)} {engagement} is outside the construction ceiling.",
    ]
    if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL):
        facts.append("Geotechnical investigation report on file.")
    if not pack_has_gap(pack.mobilisation, GAP_MASTER_PROGRAMME):
        facts.append("Master programme on file.")
    return "\n".join(
        [
            "## Source evidence and audit trail",
            "",
            *map_rows,
            "",
            "### Citation key",
            *format_citation_key_lines(citations),
            "",
            "### Audit trail",
            "- **Facts**",
            *[f"  - {fact}" for fact in facts],
            "- **Assumptions**",
            "  - Construction trade pricing, PC allowances, authority fees and unappointed consultant fees remain TBC unless stated above.",
            "- **Cost evidence conflicts**",
            "  - None identified; reconcile any tender or claim variance to the control reference.",
        ]
    )


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
            f"**Project profile / role / state:** {_project_profile_label(project)}",
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
    if mob.builder_rom:
        on_file.append("builder preliminary ROM cost advice")
    if mob.heritage_advice:
        on_file.append("heritage desktop advice")
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
    builder_ref = _ref_for_markers(refs, "builder-preliminary", "cost-advice", "builder")
    heritage_ref = _ref_for_markers(refs, "heritage")

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
            f"{'Grounded' if pack.planning_pathway_summary or mob.planning_pathway else 'Partial'} | "
            f"{planning_ref if planning_ref != '—' else heritage_ref if heritage_ref != '—' else '—'} |"
        ),
        (
            "| Geotechnical / footing class | "
            f"{'Grounded' if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL) else 'Not evidenced'} | "
            f"{geotech_ref if not pack_has_gap(pack.mobilisation, GAP_GEOTECHNICAL) else '—'} |"
        ),
    ]
    if mob.builder_rom:
        rows.append(f"| Builder ROM | On file - not a tender | {builder_ref} |")
    if mob.heritage_advice:
        rows.append(f"| Heritage advice | Grounded | {heritage_ref} |")
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
    if mob.builder_rom:
        rows.append(
            "| Builder preliminary ROM | Builder preliminary cost advice email | "
            f"{_builder_rom_amount(pack)} | ex GST | Market signal only - not tender | "
            "Reconcile to owner ceiling at tender |"
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


def _budget_cell(line: CostPlanLine) -> str:
    """Render a line's budget the way the Markdown table has always rendered it."""
    if line.budget is not None:
        return f"${line.budget:,.0f}"
    # "Grounded" is only ever set on an appointed principal certifier, whose fee is
    # owner-direct rather than unknown.
    return "Owner-direct" if line.status == "Grounded" else "TBC"


def _render_cost_breakdown(project: Project, pack: CostPlanEvidencePack) -> str:
    family = _coverage_family(project)
    is_industrial = family in {
        "industrial_warehouse",
        "industrial_process",
        "industrial_cold_chain",
        "data_centre",
    }
    is_commercial_fitout = family == "commercial_fitout"
    is_structure_only = coverage_spec(family).structure_only
    pc_allowance_rows = _PC_ALLOWANCE_ROWS_BY_FAMILY[family]
    allowance_category = (
        "Client-direct and landlord works"
        if is_commercial_fitout
        else "PC allowances"
    )

    mob = pack.mobilisation
    contingency = _money(pack.contingency_amount) if pack.contingency_amount else "TBC"
    cost_lines = cost_plan_lines(project, pack).lines

    def category_subtotal(marker: str) -> str:
        amounts = [
            line.budget
            for line in cost_lines
            if marker in line.category.lower() and line.budget is not None
        ]
        return f"${sum(amounts):,.0f}" if amounts else "TBC"

    if pack.reconciled_items:
        fee_subtotal = category_subtotal("fee")
        consultant_subtotal = category_subtotal("consult")
        construction_subtotal = category_subtotal("construct")
    else:
        fee_subtotal = _money(mob.fee_total_ex_gst)
        consultant_subtotal = "TBC"
        ceiling = _parse_amount(pack.construction_budget_ceiling)
        benchmark_pct = _CONSTRUCTION_BENCHMARK_PCT_BY_FAMILY[family]
        # Structure-only families have no benchmark split, so the subtotal stays TBC
        # even when a construction ceiling is evidenced.
        construction_subtotal = (
            f"${ceiling:,}" if benchmark_pct is not None and ceiling is not None else "TBC"
        )

    rows = [
        "| Cost Code | Category | Cost Items | Budget | Status | Basis |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    rows.extend(
        f"| {line.cost_code} | {line.category} | {line.cost_item} | "
        f"{_budget_cell(line)} | {line.status} | {line.basis} |"
        for line in cost_lines
    )

    # The grounded certifier fee is owner-direct (outside the builder contract), so it is
    # intentionally excluded from the Consultants subtotal and the grand total — same
    # treatment as owner-supplied items. Consultants subtotal stays TBC until appointments.
    subtotal_amounts = [
        _parse_amount(fee_subtotal),
        _parse_amount(consultant_subtotal),
        _parse_amount(construction_subtotal),
        _parse_amount(contingency),
    ]
    itemised_total = sum(amount for amount in subtotal_amounts if amount is not None)
    grand_total = f"${itemised_total:,}" if itemised_total else "TBC"
    grand_basis = (
        "Sum of itemised subtotals — construction is a lump-sum TBC (no rate pack), consultants TBC"
        if is_structure_only
        else "Sum of itemised subtotals — construction is benchmark % of ceiling, consultants/PC TBC"
    )
    if pack.reconciled_items:
        grand_basis = (
            "Sum of reconciled received proposal rows; proposals are not accepted or committed"
        )

    subtotal_rows = [
        f"| | | **Subtotal — Fees and charges** | {fee_subtotal} | | |",
        "| | | **Subtotal — Consultants** | TBC | | |",
        f"| | | **Subtotal — Construction** | {construction_subtotal} | | |",
    ]
    if pack.reconciled_items:
        subtotal_rows[1] = (
            f"| | | **Subtotal — Consultants** | {consultant_subtotal} | | |"
        )

    if pc_allowance_rows:
        subtotal_rows.append(
            f"| | | **Subtotal — {allowance_category}** | TBC | | |"
        )
    subtotal_rows.append(f"| | | **Subtotal — Contingency / allowances** | {contingency} | | |")
    subtotal_rows.append(f"| | | **Grand total (ex GST)** | {grand_total} | Assumption | {grand_basis} |")
    rows.extend(subtotal_rows)
    owner_lines = _owner_supplied_lines(pack.owner_supplied_items)
    cost_driver_lines: list[str] = []
    if mob.builder_rom:
        cost_driver_lines.append(f"Builder ROM market signal: {mob.builder_rom}")
    if mob.builder_rom_caveats:
        cost_driver_lines.append(
            "Builder ROM caveats: " + "; ".join(mob.builder_rom_caveats[:6]) + "."
        )
    if mob.heritage_approval_advice:
        cost_driver_lines.append(f"Heritage cost/programme driver: {mob.heritage_approval_advice}")

    if is_industrial:
        workbook_groups_line = (
            "Workbook-ready groups: Fees and charges → Consultants → Construction → "
            "Contingency / allowances."
        )
        taxonomy_line = f"Construction rows follow the {coverage_spec(family).label}."
        benchmark_line = _no_rate_pack_disclosure(family)
    elif is_commercial_fitout:
        workbook_groups_line = (
            "Workbook-ready groups: Fees and statutory charges → Consultants → "
            "Tenant construction works → Client-direct and landlord works → "
            "Contingency / allowances."
        )
        taxonomy_line = (
            "Construction rows follow the NSW Class 5 office / serviced-office "
            "commercial fit-out taxonomy structure only — no rate pack."
        )
        benchmark_line = _no_rate_pack_disclosure(family)
    elif is_structure_only:
        workbook_groups_line = (
            "Workbook-ready groups: Fees and charges → Consultants → Construction → "
            "Client/owner direct allowances (where applicable) → Contingency / allowances."
        )
        taxonomy_line = f"Construction rows follow the {coverage_spec(family).label}."
        benchmark_line = _no_rate_pack_disclosure(family)
    else:
        workbook_groups_line = (
            "Workbook-ready groups: Fees and charges → Consultants → Construction → PC allowances → "
            "Contingency / allowances."
        )
        taxonomy_line = "Construction rows follow NSW Class 1 residential taxonomy."
        benchmark_line = (
            "Construction rows are an indicative benchmark split of the owner ceiling (Assumption) "
            "until head-builder tender returns a priced schedule."
        )
    return "\n".join(
        [
            "## Cost breakdown by category",
            "",
            workbook_groups_line,
            taxonomy_line,
            benchmark_line,
            *cost_driver_lines,
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
    if pack.mobilisation.builder_rom:
        lines.append(
            f"- **Builder ROM:** {_builder_rom_amount(pack)} is a preliminary market signal only; "
            "do not treat it as tendered or contracted pricing."
        )
    for caveat in pack.mobilisation.builder_rom_caveats[:6]:
        lines.append(f"- **ROM caveat:** {caveat}.")
    if pack.mobilisation.heritage_approval_advice:
        lines.append(f"- **Heritage allowance driver:** {pack.mobilisation.heritage_approval_advice}")
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
    if pack.mobilisation.builder_rom:
        items.append("- Builder ROM is not a tender and must be checked against the tender schedule.")
    for caveat in pack.mobilisation.builder_rom_caveats[:6]:
        items.append(f"- Builder ROM caveat: {caveat}.")
    if pack.mobilisation.heritage_approval_advice:
        items.append(f"- Heritage approval/cost driver: {pack.mobilisation.heritage_approval_advice}")
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


def _render_authority_gates(
    project: Project,
    pack: CostPlanEvidencePack,
) -> str:
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
    family = _coverage_family(project)
    rows = [
        "| Gate | Status | Cost impact | Next action |",
        "| --- | --- | --- | --- |",
        f"| Planning / approval pathway | {pathway} | High if wrong | Record the confirmed pathway and cost owner |",
    ]
    if family in {"residential_class1_new", "residential_class1_refurb"}:
        rows.extend(
            [
                f"| Geotechnical / footing class | {geotech_status} | Medium–High | {geotech_action} |",
                "| Residential insurance, licence and contract evidence | Assumption | Statutory / commercial | Verify applicability and evidence before head contract |",
            ]
        )
    elif family == "building_remediation":
        rows.extend(
            [
                "| Investigation and cause confirmation | Partial | High | Close intrusive investigation and design-basis gaps before pricing |",
                "| Access, occupation and temporary controls | Assumption | High | Confirm staging, decanting and access responsibility |",
                "| Rectification verification plan | Assumption | High | Agree hold points, testing and completion evidence before tender |",
            ]
        )
    elif family == "commercial_fitout":
        rows.extend(
            [
                "| Existing-services capacity and condition | Assumption | High | Complete surveys and landlord/base-building confirmations |",
                "| Tenant, landlord and client-direct allocation | Assumption | High | Freeze the responsibility matrix before tender |",
            ]
        )
    elif family in {
        "industrial_warehouse",
        "industrial_process",
        "industrial_cold_chain",
        "data_centre",
    }:
        rows.extend(
            [
                "| Utility capacity and connection strategy | Assumption | High | Confirm applications, capacity, programme and cost allocation |",
                "| Process/vendor and building-work allocation | Assumption | High | Freeze the interface schedule before package pricing |",
                "| Commissioning and operational readiness | Assumption | High | Agree testing stages, witnesses and completion criteria |",
            ]
        )
    else:
        rows.extend(
            [
                "| Site, structure and existing-condition basis | Assumption | High | Close investigations before package pricing |",
                "| Base-building, operator and client-direct allocation | Assumption | High | Freeze the responsibility matrix before tender |",
            ]
        )
    rows.extend(
        [
            f"| Principal certifier / certification pathway | {certifier_status} | Programme | {certifier_action} |",
            "| Head-builder / package procurement | Partial | High | Tender only against a coordinated, scoped issue |",
        ]
    )
    if pack.mobilisation.heritage_approval_advice:
        rows.append(
            "| Heritage impact / approval input | Grounded | Programme / consultant fee | "
            f"{pack.mobilisation.heritage_approval_advice} |"
        )
    return "\n".join(
        [
            "## Authority, compliance and procurement gates",
            "",
            *rows,
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
            f"{_appointee_label(pack)} architect-PM engaged; fee {_money(mob.fee_total_ex_gst)} ex GST; "
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
    if mob.builder_rom:
        facts.append(mob.builder_rom)
    if mob.builder_conflict_disclosure:
        facts.append(mob.builder_conflict_disclosure)
    if mob.heritage_advice:
        facts.append(mob.heritage_advice)

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

    citations = _citation_index(pack)
    sections = [
        _render_summary(project, pack, citations),
        _render_budget_and_breakdown(project, pack, citations),
        _render_commitments_allowances(project, pack, citations),
        _render_risks_gates_actions(project, pack),
        _render_sources_and_audit(pack, citations),
    ]

    headings = required_section_headings()
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

    title = document_title()
    body = "\n\n".join(sections)
    return f"# {title}\n\n{body}\n"
