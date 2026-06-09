"""Section-level content contracts for platform_seeded Create Cost Plan drafts."""

from __future__ import annotations

from app.sitewise.pmp_greenfield_brief import (
    ARCHETYPE_OVERLAYS,
    GREENFIELD_DATE_RULE,
    ROLE_OVERLAYS,
    _adapt_due_diligence_for_state,
    _archetype_due_diligence_checklist,
    _state_note,
)

COST_BREAKDOWN_TABLE = """
Include this cost breakdown table under **Cost breakdown by category** using workbook-ready groups.
Use short stable **Cost Item** labels (2–5 words) suitable for future Excel lookup — not long sentences.
All figures ex GST unless the GST basis section states otherwise.

| Cost Code | Category | Cost Items | Budget | Status | Basis |
| --- | --- | --- | --- | --- | --- |
| 1 | Fees and charges | Planning fees | TBC | Assumption | Benchmark |
| 2 | Fees and charges | Certifier fees | TBC | Assumption | Benchmark |
| 3 | Consultants | Architect / PM | TBC | Assumption | Fee proposal or benchmark |
| 4 | Consultants | Structural engineer | TBC | Assumption | Benchmark |
| 5 | Consultants | Surveyor | TBC | Assumption | Benchmark |
| 6 | Construction | Preliminaries | TBC | Assumption | HIA schedule or claim |
| 7 | Construction | Siteworks | TBC | Assumption | Benchmark |
| 8 | Construction | Footings and slab | TBC | Assumption | Benchmark |
| 9 | Construction | Framing | TBC | Assumption | Benchmark |
| 10 | Construction | External envelope | TBC | Assumption | Benchmark |
| 11 | Construction | Partitions and doors | TBC | Assumption | Benchmark |
| 12 | Construction | Kitchen and bathrooms | TBC | Assumption | PC sums |
| 13 | Construction | Building services | TBC | Assumption | Benchmark |
| 14 | Contingency / allowances | Construction contingency | TBC | Assumption | 5–10% construction |
| | | **Subtotal — Fees and charges** | | | |
| | | **Subtotal — Consultants** | | | |
| | | **Subtotal — Construction** | | | |
| | | **Subtotal — Contingency / allowances** | | | |
| | | **Grand total (ex GST)** | | | |

Adapt Cost Items to project archetype and role. Separate owner-supplied items below the main table.
"""

BUDGET_RECONCILIATION_TABLE = """
When multiple budget figures exist (or in platform_seeded mode as a scaffold), include:

| Figure | Source | Amount (ex GST) | GST basis | Status | Adopted? |
| --- | --- | --- | --- | --- | --- |
| Owner stated budget | Assumption | TBC | Unknown | Assumption | Qualified |
| PMP / fee proposal note | Assumption | TBC | ex GST | Assumption | — |
| QS / cost manager report | Assumption | TBC | ex GST | Assumption | — |
| **Cost-control reference** | — | TBC | ex GST | Assumption | Adopted for planning |
"""

AUTHORITY_GATES_TABLE = """
Include under **Authority, compliance and procurement gates**:

| Gate | Status | Cost impact | Next action |
| --- | --- | --- | --- |
| Planning pathway (CDC vs DA) | Assumption | High if wrong | Confirm before spend |
| Geotechnical / footing class | Assumption | Medium–High | Commission if absent |
| HBCF / HOW / licence (if triggered) | Assumption | Statutory | Verify before contract |
| Certifier appointment | Assumption | Programme | Appoint before CC |
"""

SECTION_BRIEFS: dict[str, str] = {
    "Project name and location": """
- Project title from archetype overlay or **Assumption: [Project title]**.
- Site address: **Assumption: not yet evidenced** unless project evidence supplies it.
- Archetype, role, and state declared.
""",
    "Source evidence used": """
- List doctrine, seeds, and project evidence consulted (or state none yet for platform_seeded).
- For evidence_grounded: include **Evidence on file:** line and evidence map table:
  | Section | Evidence status | Ref |
- Separate **Gaps** for missing cost evidence (budget, contract, claims, fee proposals).
""",
    "Budget reconciliation and control decision": """
- Include the budget reconciliation table from the contract appendix when any competing figures exist.
- State the cost-control reference figure and why it was adopted or qualified.
- If an affordability gap exists, frame as a Principal/owner decision (increase budget, reduce scope, phase, pause).
""",
    "Total approved or indicative budget": """
- Single headline total (ex GST) aligned to the cost-control reference.
- Separate construction cost vs total project cost if consultant/authority fees are outside construction.
- Label as Approved, Indicative, or Assumption.
""",
    "GST basis": """
- State explicitly: **All workbook figures exclude GST** (Create Cost Plan v1 default).
- Note residential owner-facing convention: owners often think inc GST — translate where helpful.
- If evidence uses inc GST, show derivation to ex GST.
""",
    "Cost breakdown by category": """
- Include the cost breakdown table from the contract appendix.
- Groups in order: Fees and charges, Consultants, Construction, Contingency / allowances.
- Do NOT collapse Construction to one line when claim/contract evidence supports trade breakdown.
- Owner-supplied items listed separately below the table.
""",
    "Known locked contract and appointment values": """
- Table of locked appointments/contracts with supplier, amount ex GST, date, and evidence ref.
- **Assumption: none locked yet** if platform_seeded.
""",
    "Allowances and contingency": """
- PC sums, provisional sums, owner-supplied allowances — each labelled.
- Construction contingency: basis and percentage (typically 5–10% residential on construction only).
- Do not use contingency as a dumping ground for unresolved scope.
""",
    "PM fee treatment": """
- State whether architect-PM / PM fee is inside or outside the stated project budget.
- If fee proposal on file, ground the amount; otherwise Assumption.
""",
    "Assumptions and exclusions": """
- Bulleted assumptions and exclusions affecting cost certainty.
- Distinguish benchmark estimates from evidenced amounts.
""",
    "Risks and review questions": """
- Minimum 5 cost risks in table form: Risk | Impact | Owner | Next action | Due.
- Review questions for the PM (specific, not generic).
""",
    "Authority, compliance and procurement gates": """
- Include the authority gates table from the contract appendix.
- Treat informal builder advice and open-ended cost-plus as governance risks, not budget facts.
""",
    "Recommended next steps": """
- Numbered next steps with owner asks and relative due dates.
- Include workbook export readiness note: markdown review before Excel update.
""",
    "Internal audit layer": """
- Bullet lists: **Facts**, **Assumptions**, **Judgements**, **Recommendations** (min 3).
- **Cost evidence conflicts** subsection if claim schedules and variations disagree.
- Repeat mandatory seed paths under "Mandatory seeds consulted".
- Workflow warnings for missing budget, unsorted inbox, stale cost plan.
""",
}

GREENFIELD_QUALITY_MARKERS: dict[tuple[str, str], tuple[str, ...]] = {
    ("new-dwelling", "architect-pm"): (
        "contingency",
        "ex gst",
        "fees and charges",
        "construction",
        "recommendation",
    ),
    ("renovation", "architect-pm"): (
        "contingency",
        "latent",
        "ex gst",
        "recommendation",
    ),
    ("multi-dwelling", "architect-pm"): (
        "contingency",
        "classification",
        "ex gst",
    ),
    ("ancillary", "architect-pm"): ("contingency", "cdc", "ex gst"),
    ("small-commercial", "architect-pm"): ("contingency", "ex gst", "reduced"),
    ("new-dwelling", "owner-builder"): ("contingency", "owner-supplied", "recommendation"),
    ("renovation", "owner-builder"): ("contingency", "latent", "recommendation"),
    ("new-dwelling", "builder"): ("contingency", "hbcf", "stage", "recommendation"),
    ("renovation", "builder"): ("contingency", "variation", "latent", "recommendation"),
    ("new-dwelling", "d-and-c"): ("contingency", "design", "recommendation"),
}


def greenfield_quality_markers(*, archetype: str, user_role: str) -> tuple[str, ...]:
    return GREENFIELD_QUALITY_MARKERS.get(
        (archetype, user_role),
        ("contingency", "ex gst", "recommendation", "assumption"),
    )


def greenfield_markers_missing(markdown: str, *, archetype: str, user_role: str) -> list[str]:
    haystack = markdown.lower()
    return [
        marker
        for marker in greenfield_quality_markers(archetype=archetype, user_role=user_role)
        if marker not in haystack
    ]


def greenfield_structure_violations(
    markdown: str,
    *,
    _archetype: str = "",
    _user_role: str = "",
) -> list[str]:
    issues: list[str] = []
    breakdown = _markdown_section(markdown, "Cost breakdown by category").lower()
    if breakdown and "fees and charges" not in breakdown:
        issues.append("Cost breakdown must include Fees and charges group")
    if breakdown and "consultants" not in breakdown:
        issues.append("Cost breakdown must include Consultants group")
    if breakdown and "construction" not in breakdown:
        issues.append("Cost breakdown must include Construction group")
    if breakdown and "contingency" not in breakdown:
        issues.append("Cost breakdown must include Contingency / allowances group")
    gst = _markdown_section(markdown, "GST basis").lower()
    if gst and "gst" not in gst:
        issues.append("GST basis section must state GST treatment explicitly")
    return issues


def _markdown_section(markdown: str, heading: str) -> str:
    target = heading.strip().lower()
    lines = markdown.splitlines()
    section_lines: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("## ") and stripped[3:].strip() == target:
            collecting = True
            continue
        if collecting and stripped.startswith("## "):
            break
        if collecting:
            section_lines.append(line)
    return "\n".join(section_lines)


EVIDENCE_GROUNDED_CONTRACT = """
## Evidence-grounded content contract (MUST follow)

Ground budget figures, appointments, and claim rows from Sources. Include **Evidence on file:** and the
evidence map table in Source evidence used. Apply the claim-first rule when progress claims or SOV appear
in Sources — preserve trade/work-package granularity in Construction.

Use workbook-ready cost breakdown groups: Fees and charges, Consultants, Construction, Contingency / allowances.
Table columns: Cost Code | Category | Cost Items | Budget | Status | Basis.

Internal audit layer: bullet lists **Facts**, **Assumptions**, **Judgements**, **Recommendations** (min 3).
Label unknown values as **Assumption** only where Sources are silent.

Use these exact blocks in evidence_grounded mode (copy the structure; fill from Sources):

**Source evidence used**
**Evidence on file:** [comma-separated list of project documents from Sources]

| Section | Evidence status | Ref |
| --- | --- | --- |
| Cost breakdown by category | Grounded / Partial / Not evidenced | [source ref] |

**Internal audit layer** — use `- **Facts**` as a bullet label (NOT `### Facts`):
- **Facts**
- [concrete evidenced bullet from Sources]
- **Assumptions**
- **Judgements**
- **Recommendations**
"""


def build_greenfield_brief(
    *,
    archetype: str,
    user_role: str,
    state: str,
    draft_mode: str = "platform_seeded",
) -> str:
    if draft_mode == "evidence_grounded":
        role_overlay = ROLE_OVERLAYS.get(user_role, "")
        archetype_overlay = ARCHETYPE_OVERLAYS.get(archetype, "").strip()
        parts = [
            EVIDENCE_GROUNDED_CONTRACT.strip(),
            _state_note(state),
            GREENFIELD_DATE_RULE.strip(),
            role_overlay.strip(),
            archetype_overlay.strip(),
        ]
        return "\n".join(part for part in parts if part.strip())

    role_overlay = ROLE_OVERLAYS.get(user_role, "")
    archetype_overlay = ARCHETYPE_OVERLAYS.get(archetype, "").strip()
    due_diligence = _archetype_due_diligence_checklist(archetype, state=state)
    if due_diligence:
        due_diligence = _adapt_due_diligence_for_state(due_diligence, state)

    parts = [
        "## Greenfield content contract (platform_seeded — MUST follow)",
        _state_note(state),
        GREENFIELD_DATE_RULE.strip(),
        role_overlay.strip(),
        archetype_overlay.strip(),
        "",
        COST_BREAKDOWN_TABLE.strip(),
        "",
        BUDGET_RECONCILIATION_TABLE.strip(),
        "",
        AUTHORITY_GATES_TABLE.strip(),
        "",
        "Populate every required ## section. Use tables — not single generic paragraphs.",
        "Label unknown values as **Assumption**. Cost Items must stay short and stable.",
        "",
    ]
    for heading, brief in SECTION_BRIEFS.items():
        parts.append(f"### Section: {heading}")
        parts.append(brief.strip())
        parts.append("")
    return "\n".join(parts)
