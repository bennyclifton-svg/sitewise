"""Section-level content contracts for platform_seeded Create PMP drafts."""

from __future__ import annotations

from typing import Any

from app.sitewise.section_contracts import (
    PMP_SECTION_HEADINGS,
    heading_for_section_id,
)
from app.sitewise.taxonomy import (
    RiskFlag,
    complexity_option_labels,
    work_scope_items_for,
)

# Cross-cutting markers every architect-PM greenfield draft must contain.
ARCHITECT_PM_COMMON_MARKERS: tuple[str, ...] = (
    "what this means",
    "slab",
    "lockup",
    "invited",
    "recommendation",
)

# Mandatory due diligence tables surfaced under Approvals and compliance.
ARCHETYPE_DUE_DILIGENCE_CHECKLISTS: dict[str, str] = {
    "new-dwelling": """
### Due diligence checklist (open until evidenced) — new-dwelling
Include this table under **Approvals and compliance** (every row status = Assumption until filed):

| Item | Status | Filing path | Next action |
| --- | --- | --- | --- |
| Survey / title boundary | Assumption | `03-design/01-due-diligence/` | Commission registered surveyor |
| Dilapidation (adjoining) | Assumption | `03-design/01-due-diligence/` | Commission dilapidation report |
| Geotechnical / AS 2870 class | Assumption | `03-design/01-due-diligence/` | Commission soil report |
| Stormwater / OSD | Assumption | `03-design/01-due-diligence/` | Confirm drainage strategy |
| Sydney Water sewer diagram / BOS | Assumption | `03-design/01-due-diligence/` | Obtain sewer diagram |
| BAL / bushfire | Assumption | `03-design/01-due-diligence/` | Confirm BAL requirement |
| Flood / heritage | Assumption | `03-design/01-due-diligence/` | Desktop planning check |
| Services capacity | Assumption | `03-design/01-due-diligence/` | Confirm utility capacity |
""",
    "renovation": """
### Due diligence checklist (open until evidenced) — renovation
Include this table under **Approvals and compliance** (every row status = Assumption until filed):

| Item | Status | Filing path | Next action |
| --- | --- | --- | --- |
| Survey / measure-up | Assumption | `03-design/01-due-diligence/` | Commission surveyor |
| Dilapidation (neighbours + retained fabric) | Assumption | `03-design/01-due-diligence/` | Commission dilapidation |
| Existing structure assessment | Assumption | `03-design/01-due-diligence/` | Structural review |
| Services locating | Assumption | `03-design/01-due-diligence/` | Dial-before-you-dig / scan |
| Hazardous materials | Assumption | `03-design/01-due-diligence/` | Hazmat assessment if pre-1980 |
| Moisture / termite / rot | Assumption | `03-design/01-due-diligence/` | Building inspection |
| Heritage / character controls | Assumption | `03-design/01-due-diligence/` | Planning controls check |
| BASIX alteration trigger (NSW ≥ $50k) | Assumption | `03-design/01-due-diligence/` | Confirm BASIX obligation |
| Approval pathway (CDC vs DA) | Assumption | `00-brief-pmp/` | Test pathway before spend |
""",
    "multi-dwelling": """
### Due diligence checklist (open until evidenced) — multi-dwelling
Include this table under **Approvals and compliance** (every row status = Assumption until filed):

| Item | Status | Filing path | Next action |
| --- | --- | --- | --- |
| NCC classification gate (Class 1a vs Class 2) | Assumption | `00-brief-pmp/` | Certifier confirmation |
| Consent conditions register | Assumption | `03-design/01-due-diligence/` | Extract conditions early |
| Subdivision / strata pathway | Assumption | `03-design/01-due-diligence/` | Confirm titling strategy |
| Infrastructure contributions | Assumption | `03-design/01-due-diligence/` | Council / agency check |
| OSD / stormwater strategy | Assumption | `03-design/01-due-diligence/` | Hydraulic assessment |
| Waste / collection strategy | Assumption | `03-design/01-due-diligence/` | Confirm collection design |
| Separate metering (if applicable) | Assumption | `03-design/01-due-diligence/` | Utility consultation |
| Staged OC / partial handover | Assumption | `00-brief-pmp/` | Programme staging decision |
""",
    "ancillary": """
### Due diligence checklist (open until evidenced) — ancillary
Include this table under **Approvals and compliance** (every row status = Assumption until filed):

| Item | Status | Filing path | Next action |
| --- | --- | --- | --- |
| NCC class fork (Class 1a secondary vs Class 10a/10b) | Assumption | `00-brief-pmp/` | Confirm classification |
| Housing SEPP CDC eligibility test | Assumption | `03-design/01-due-diligence/` | Test CDC vs DA fallback |
| BASIX trigger (Class 1a secondary) | Assumption | `03-design/01-due-diligence/` | Confirm BASIX obligation |
| Tie-in to primary dwelling services | Assumption | `03-design/01-due-diligence/` | Services capacity check |
| Stormwater / access coordination | Assumption | `03-design/01-due-diligence/` | Site coordination review |
""",
    "small-commercial": """
### Due diligence checklist (open until evidenced) — small-commercial
Include this table under **Approvals and compliance** (every row status = Assumption until filed):

| Item | Status | Filing path | Next action |
| --- | --- | --- | --- |
| Builder licence endorsement (commercial) | Assumption | `00-brief-pmp/` | Verify licence class |
| NCC Volume One applicability | Assumption | `00-brief-pmp/` | Confirm classification |
| Accessibility (AS 1428) | Assumption | `03-design/01-due-diligence/` | Early accessibility review |
| Fire compartmentation | Assumption | `03-design/01-due-diligence/` | Fire engineer if required |
| Commercial certifier accreditation | Assumption | `03-design/01-due-diligence/` | Confirm certifier scope |
| `confidence: reduced` flag | Assumption | `00-brief-pmp/` | Recommend commercial PM/QS |
""",
}

ARCHITECT_PM_PROGRAMME_SUBMILESTONE_TABLE = """
Include this sub-milestone table under **Programme and staging regime** (status Assumption; durations TBC):

| Sub-milestone | Maps to stage | Status | Note |
| --- | --- | --- | --- |
| Site due diligence complete | Stage 1 | Assumption | Per archetype checklist |
| Planning pathway confirmed | Stage 1 | Assumption | CDC / DA / exempt |
| DA/CDC lodged and determined | Stage 1 | Assumption | Authority gate |
| CC issued (LSL receipt prerequisite) | Stage 1→2 | Assumption | CC-blocking items |
| Builder procured / contract executed | Stage 2→3 | Assumption | 2–3 invited builders |
| Construction start / site possession | Stage 3 | Assumption | Mobilisation gate |
| Slab / substructure | Stage 3 | Assumption | Inspection gate |
| Frame | Stage 3 | Assumption | Inspection gate |
| Lockup | Stage 3 | Assumption | Envelope sealed |
| Fixing | Stage 3 | Assumption | Internal trades |
| Practical completion (PC) | Stage 3 | Assumption | Defects schedule |
| OC issued | Stage 3 | Assumption | Occupation gate |
| Defects liability period (DLP) | Post-OC | Assumption | Per contract |
"""

BUILDER_PROGRAMME_SUBMILESTONE_TABLE = """
Include this sub-milestone table under **Programme and staging regime** (status Assumption; durations TBC).
The drafter IS the builder — do NOT include "builder procured" or "invited builders" rows.

| Sub-milestone | Maps to stage | Status | Note |
| --- | --- | --- | --- |
| Mobilisation checklist complete (HBCF, LSL, CWI, licence) | Pre-start | Assumption | Per setup-and-commission-guide |
| Head contract executed | Pre-start | Assumption | Tender/contract basis filed |
| Planning permit / CC issued | Pre-start | Assumption | Authority gate |
| Site due diligence complete | Pre-start | Assumption | Per archetype checklist |
| Construction start / site possession | Construction | Assumption | Mobilisation gate |
| Enabling works / demolition (renovation) | Construction | Assumption | Staging if live occupancy |
| Slab / substructure | Construction | Assumption | HIA stage claim + inspection gate |
| Frame | Construction | Assumption | HIA stage claim + inspection gate |
| Lockup | Construction | Assumption | Envelope sealed — stage claim gate |
| Fixing | Construction | Assumption | Internal trades — stage claim gate |
| Practical completion (PC) | Construction | Assumption | Defects schedule |
| OC issued | Handover | Assumption | Occupation gate |
| Defects liability period (DLP) | Post-OC | Assumption | Per contract |
"""

OWNER_BUILDER_PROGRAMME_SUBMILESTONE_TABLE = """
Include this sub-milestone table under **Programme and staging regime** (status Assumption; durations TBC).
The drafter IS the owner-builder — do NOT include "builder procured" or "invited builders" rows.

| Sub-milestone | Maps to stage | Status | Note |
| --- | --- | --- | --- |
| Owner-builder permit confirmed (if required) | Pre-start | Assumption | Gate before site start |
| Planning permit / CC issued | Pre-start | Assumption | Authority gate |
| Site due diligence complete | Pre-start | Assumption | Per archetype checklist |
| Trade packages procured | Pre-start | Assumption | Per trade register |
| Construction start / site possession | Construction | Assumption | Mobilisation gate |
| Slab / substructure | Construction | Assumption | Inspection gate |
| Frame | Construction | Assumption | Inspection gate |
| Lockup | Construction | Assumption | Envelope sealed |
| Fixing | Construction | Assumption | Internal trades |
| Practical completion (PC) | Construction | Assumption | Defects schedule |
| OC issued | Handover | Assumption | Occupation gate |
| Defects liability period (DLP) | Post-OC | Assumption | Statutory warranty if sold |
"""

D_AND_C_PROGRAMME_SUBMILESTONE_TABLE = BUILDER_PROGRAMME_SUBMILESTONE_TABLE.replace(
    "The drafter IS the builder",
    "The drafter IS the D&C contractor",
)

PROGRAMME_SUBMILESTONE_TABLE = ARCHITECT_PM_PROGRAMME_SUBMILESTONE_TABLE

PROGRAMME_SUBMILESTONE_TABLES: dict[str, str] = {
    "architect-pm": ARCHITECT_PM_PROGRAMME_SUBMILESTONE_TABLE,
    "builder": BUILDER_PROGRAMME_SUBMILESTONE_TABLE,
    "owner-builder": OWNER_BUILDER_PROGRAMME_SUBMILESTONE_TABLE,
    "d-and-c": BUILDER_PROGRAMME_SUBMILESTONE_TABLE,
}

AUTHORITY_TRACKER_TABLE = """
Include this authority tracker table under the planning/approvals section (status Assumption):

| Authority / instrument | Status | Responsible party | Next action |
| --- | --- | --- | --- |
| Building surveyor / certifier | Assumption | Owner | Appoint before CC |
| Planning permit / DA or CDC | Assumption | Owner / builder | Confirm pathway |
| Construction Certificate / building permit | Assumption | Certifier | Issue before site start |
| Occupation Certificate / occupancy permit | Assumption | Certifier | Issue at handover |
| Utility connections (power, water, sewer) | Assumption | Owner / builder | Confirm capacity |
"""

SUBCONTRACTOR_REGISTER_STARTER = """
Include this subcontractor register starter under **Procurement and subcontractor posture**
(name at least 5 trades — do NOT fill every cell with the word "Assumption"):

| Trade | Appointed | Licence verified | Insurance | Scope stage | Status |
| --- | --- | --- | --- | --- | --- |
| Demolition / enabling | TBC | Assumption | Assumption | Pre-start | Assumption |
| Structural carpentry | TBC | Assumption | Assumption | Construction | Assumption |
| Plumbing / hydraulic | TBC | Assumption | Assumption | Construction | Assumption |
| Electrical | TBC | Assumption | Assumption | Construction | Assumption |
| Waterproofing | TBC | Assumption | Assumption | Construction | Assumption |
| Plaster / lining | TBC | Assumption | Assumption | Fixing | Assumption |
"""

RISK_REGISTER_TABLE = """
Include this risk register table under **Risks, decisions and next actions** (not a numbered prose list):

| Risk | Owner | Status | Next action | Due |
| --- | --- | --- | --- | --- |
| (archetype-specific risk 1) | Builder | Assumption | (specific action) | (relative date) |
| (archetype-specific risk 2) | Builder | Assumption | (specific action) | (relative date) |
| (archetype-specific risk 3) | Owner | Assumption | (specific action) | (relative date) |
| (archetype-specific risk 4) | Builder | Assumption | (specific action) | (relative date) |
| (archetype-specific risk 5) | Builder | Assumption | (specific action) | (relative date) |
"""

GREENFIELD_DATE_RULE = """
### Date rule (mandatory for all register rows and recommendations)
- Never invent past calendar dates.
- Use either relative phrasing ("within 2 weeks of engagement", "before scheme lock"), OR
- ISO dates 2–4 weeks after the mobilisation run date supplied in the prompt.
"""

# Archetype-specific content the PM-facing sections must surface even without evidence.
ARCHETYPE_OVERLAYS: dict[str, str] = {
    "new-dwelling": """
### Archetype overlay — new-dwelling (Class 1a, NCC Volume Two)
- NCC Class 1a detached dwelling on a cleared or knockdown-rebuild site.
- Site due diligence before scheme lock: survey, dilapidation, geotechnical/soil report (AS 2870 class), stormwater/OSD, Sydney Water sewer diagram, BAL, flood, heritage, services capacity.
- Planning pathway must be tested — do not assume CDC: exempt vs CDC (SEPP complying) vs DA + CC. Record pathway as an open decision until evidenced.
- NSW approvals stack: BASIX certificate (commitment-based), principal certifier, CC (LSL receipt is CC-blocking), OC, BASIX final at handover.
- Typical consultant set to open/track: architect, structural engineer, hydraulic consultant, BASIX assessor, surveyor, geotechnical (if reactive site), certifier, landscape (if required).
- Builder procurement (architect-PM): formal head-builder selection — typically 2–3 invited builders, agreed evaluation criteria before tender close, one clear recommendation to owner.
- Archetype risks to name: planning pathway uncertainty, reactive soil / footing type, BASIX commitment flow-through, utility lead times, weather/programme slip.
""",
    "renovation": """
### Archetype overlay — renovation (existing building is evidence, constraint, and risk)
- Renovation posture: locate before disturb; record before change; decide before spend; treat tie-ins as high risk.
- Due diligence package before concept lock: survey/measure-up, dilapidation (neighbours + retained fabric), existing structure, services locating, hazardous materials, moisture/termite/rot, heritage/character, BASIX alteration trigger (NSW ≥ $50k), approval pathway.
- Latent conditions are common not exceptional — price with contingency, provisional sums, or staged investigation; do not programme as if walls are empty.
- Live occupancy and staging may apply — temporary kitchen/bathroom, dust/noise, temporary weatherproofing.
- Waterproofing and old-to-new tie-ins are primary failure zones (wet areas, balconies, roof junctions, slab junctions).
- NSW BASIX applies to alterations/additions at the stated value trigger — flow commitments through procurement and handover.
- Builder procurement (architect-PM): formal head-builder selection — typically 2–3 invited builders where engagement includes procurement.
- Specialist reports (geotechnical, survey, dilapidation) are owner-commissioned — the architect-PM coordinates appointments, it does not obtain or issue them. Frame recommendations as "coordinate owner's appointment", never "obtain/issue".
""",
    "multi-dwelling": """
### Archetype overlay — multi-dwelling
- Classification gate first: Class 1a attached townhouses vs Class 2 apartments — do not assume; certifier confirmation required.
- Use a detailed staged regime (not only the 3-stage baseline): design/approvals, procurement, enabling, structure, envelope/services/finishes, commissioning, OC, handover, DLP — map back to baseline stages.
- Extra approval evidence: consent conditions register, subdivision/strata pathway, infrastructure contributions, OSD/stormwater, waste/collection strategy, separate metering if applicable.
- Consent conditions are live delivery obligations — extract before procurement/site start.
- Staged OC / partial handover may apply — programme and defects registers must reflect staging.
- Builder procurement (architect-PM): formal head-builder selection — typically 2–3 invited builders, evaluation matrix before tender close.
""",
    "ancillary": """
### Archetype overlay — ancillary (granny flat, studio, garage, shed)
- NCC class fork first: Class 1a secondary dwelling (habitable, kitchen+bath) vs Class 10a/10b ancillary — drives BASIX, OC, and inspection regime.
- NSW default pathway for secondary dwellings: Housing SEPP CDC eligibility test (lot size, 60 sqm cap, setbacks, bushfire/flood/heritage exclusions) — DA fallback if CDC fails.
- BASIX applies to Class 1a secondary dwellings above cost threshold; Class 10a studios typically do not trigger BASIX.
- Tie-in to existing primary dwelling services, stormwater, and access is a coordination risk when the primary house is retained.
""",
    "small-commercial": """
### Archetype overlay — small-commercial (reduced confidence)
- Frontmatter/confidence: SiteWise residential harness at edge of domain — flag `confidence: reduced` and recommend commercial PM/QS/certifier for material scope.
- Hard stop: confirm builder licence endorsement covers commercial work — residential licence alone is not sufficient.
- NCC Volume One applies (not Volume Two); BASIX does not apply — Section J / NatHERS commercial pathways differ.
- Accessibility (AS 1428), fire compartmentation, and commercial certifier accreditation differ from residential.
""",
}

ROLE_ARCHITECT_PM_OVERLAY = """
### Role overlay — architect-PM
- Client-side advisor to residential owner — not the builder, certifier, or Superintendent unless expressly appointed in writing.
- Two briefs: (1) architect-PM engagement brief — fee, scope, PMP, governance; (2) owner project brief — what is being built. Do not merge.
- Role declaration defaults until evidenced: architect/PM advisory yes; Superintendent no; Certifier no; contract administrator only if engagement says so.
- PI insurance currency and scope must be recorded before procurement/contract-administration reliance.
- Builder evidence the architect-PM verifies (does not hold): licence + QS, HBCF/HOW per-project certificate, LSL receipt before CC, executed head contract, CWI/PL/workers comp.
- Owner escalation format (mandatory in Communications protocol):
  1. What this means for you
  2. What we need from you (with due date)
  3. What's happened
  4. What's next
  5. Background (if needed)
- Give recommendations, not option bundles without a view.
"""

ROLE_OWNER_BUILDER_OVERLAY = """
### Role overlay — owner-builder
- Principal and contractor simultaneously — no builder-side HBCF/HOW for own work; statutory warranty to future buyers if sold within 7 years 6 months.
- Owner-builder permit required where trigger applies — gate before certifier appointment/site start.
- Park-for-decision queue under `08-meetings-reporting/` for self-decisions.
- Trade register: licence, insurance, scope, HBCF (where contractor package triggers), payment checks per trade.
"""

ROLE_BUILDER_OVERLAY = """
### Role overlay — builder
- Head contract with owner — HOW/HBCF, LSL, licence, CWI, PL, workers comp are builder-held instruments.
- Brief basis is accepted tender/contract — scope via drawings/specifications, exclusions, PC/provisional sums, owner-supplied items.
- HIA stage-payment milestones link to programme: slab, frame, lockup, fixing, completion — verify physical completion before certifying claims.
- Variation mechanism (MANDATORY): HIA Schedule of Variations or equivalent — price and obtain owner signature before work begins; maintain variation register under `07-construction/06-variations/`.
- Renovation archetype: latent conditions are common — contingency, provisional sums, and staged investigation; do not programme as if walls are empty.
"""

BUILDER_SECTION_BRIEFS: dict[str, str] = {
    "Evidence basis and document control": """
- Status: draft mobilisation plan, not issued. Version v01.
- Source hierarchy: project evidence (none yet) → doctrine → seeds in seed_consulted.
- Document control: save under `00-brief-pmp/`; supersede when contract/tender evidence arrives.
""",
    "Project overview": """
- State declared archetype, role, state, and mobilisation status: **Assumption: pre-contract mobilisation** (do not invent a construction phase).
- One-sentence project type from archetype overlay.
- **Assumption**: site address, contract sum, owner identity, and tender basis not yet filed.
""",
    "Builder role and contract basis": """
- Head contract posture: HIA Lump Sum / Renovation or equivalent — stage payments, variation mechanism, EOT clause.
- Scope basis: drawings, specifications, exclusions, PC/provisional sums, owner-supplied items — all **Assumption** until tender/contract filed.
- Variation discipline: every scope change via written variation (HIA Schedule of Variations) before work begins.
- EOT discipline: contemporaneous notice within contract window, supported by programme and evidence.
- Owner communication: plain-English summary with contractual attachment for variations, claims, and EOT.
""",
    "Statutory instruments and insurance": """
- Builder-held instruments table with columns Instrument | Status | Filing path | Next action (not Instrument | Status only).
- Required rows: licence + QS, HBCF/HOW per-project certificate, LSL receipt, CWI, PL, workers comp.
- For non-NSW state: inline state gap callout for HBCF/HOW/LSL equivalents — do not extend NSW silently.
""",
    "Planning and approvals pathway": """
- Include the archetype due diligence checklist table (every row status = Assumption; adapt NSW-specific rows for state).
- Planning pathway: CDC vs DA vs exempt — open decision until evidenced.
- Include the authority tracker table (see contract appendix).
""",
    "Programme and staging regime": """
- Include the role-specific sub-milestone table from the contract appendix (builder rows — no "invited builders").
- HIA stage-payment milestones mapped to programme gates: slab, frame, lockup, fixing, completion.
- Renovation: enabling works / demolition staging, live occupancy, temporary weatherproofing, tie-in sequencing.
""",
    "Procurement and subcontractor posture": """
- Include the subcontractor register starter table (named trades — not placeholder "Assumption" in every cell).
- Cost posture: contingency 5–10% for renovation latent conditions; PC sums and provisional sums tracked separately.
- Subcontractor variation assessment: builder assesses subbie variations; owner variations via head contract mechanism.
- Owner-supplied items tracked separately from contract sum.
""",
    "Risks, decisions and next actions": """
- Include the risk register table (Risk | Owner | Status | Next action | Due) — minimum 5 rows, not a numbered prose list.
- Open owner decisions table: Decision | Recommended default | Owner | Due date.
- Renovation risks to include: latent conditions, tie-ins, waterproofing, live occupancy, approval pathway uncertainty.
""",
    "Internal audit layer": """
- Use bullet lists labelled **Facts**, **Assumptions**, **Judgements**, **Recommendations** — do NOT use ### subheadings.
- Minimum 3 Recommendations, each with an owner ask and due date.
- Draft register rows table (ID, description, owner, status, due date, source, next action).
- Workflow warnings: no head contract, no HBCF certificate, unsorted `_inbox/` (exact wording).
- Repeat mandatory seed paths under "Mandatory seeds consulted".
""",
}

ROLE_D_AND_C_OVERLAY = """
### Role overlay — D&C
- Inherits all builder obligations plus design responsibility: design fee/programme, design responsibility matrix, consultant PI, D&C PI, certifier submission protocol.
- Design pack controlled before construction release — certifier must not receive stale submissions.
- Novation/appointment evidence for design consultants must be visible at setup.
"""

ROLE_OVERLAYS: dict[str, str] = {
    "architect-pm": ROLE_ARCHITECT_PM_OVERLAY,
    "owner-builder": ROLE_OWNER_BUILDER_OVERLAY,
    "builder": ROLE_BUILDER_OVERLAY,
    "d-and-c": ROLE_D_AND_C_OVERLAY,
}

ARCHITECT_PM_SECTION_BRIEFS: dict[str, str] = {
    "Evidence basis and document control": """
- Status: draft, review-only, not issued. Version v01.
- Source hierarchy: project evidence (none yet) → doctrine → seeds listed in seed_consulted.
- Document control: save under `00-brief-pmp/`; supersede with next version when evidence arrives.
- Decision register to open under `08-meetings-reporting/` (append-only per decision-discipline).
""",
    "Project overview": """
- State declared archetype, role, state, and current mobilisation phase (pre-brief / pre-engagement).
- One-sentence project type from archetype overlay.
- **Assumption**: site address, dwelling type, budget, and owner identity not yet evidenced.
""",
    "Architect-PM role and appointment": """
- Default role declaration table: Architect/PM (advisory) | Superintendent (no, unless appointed) | Certifier (no) | Contract administrator (per engagement).
- Engagement instruments gap: fee proposal, executed engagement letter, scope of services — all **Assumption: not yet filed**.
- PI insurance: record required fields (holder, period, limit, exclusions) as gaps to verify.
- Builder instruments: verification checklist (licence, HBCF/HOW, LSL, insurance, contract) — verify only, not held by architect-PM.
""",
    "Two-brief discipline": """
- Table or bullet pair separating engagement brief vs owner project brief with different decision routes.
- Examples of what belongs where (extra tender round = engagement; bigger kitchen = project brief).
- **Assumption**: neither brief filed yet — list minimum contents each must capture when drafted.
""",
    "Governance and decisions": """
- RACI-style matrix: Owner decides | Architect-PM recommends | Consultants advise | Builder executes | Certifier certifies.
- Decision gates: planning pathway, scheme endorsement, builder award, contract signature, CC issue, PC/OC.
- All decisions append-only per decision-discipline; file under `08-meetings-reporting/`.
""",
    "Communications protocol": """
- Owner update cadence (**Assumption**: monthly owner update + milestone emails).
- Forums: owner update, consultant coordination, builder RFIs (post-award), authority/certifier route.
- Emergency contact route.
- Owner escalation format (MANDATORY — use for material decisions):
  1. What this means for you
  2. What we need from you (with due date)
  3. What's happened
  4. What's next
  5. Background (if needed)
- Give a clear recommendation in escalations — not an option bundle without a view.
""",
    "Fee, services and programme relationship": """
- Fee basis placeholders: fixed fee / percentage / staged fee milestones mapped to PMP stages.
- Service exclusions to watch: extra tender rounds, contract administration beyond scope, additional authority submissions.
- Owner/authority delay affect on fee/programme — extension mechanism as **Assumption** until engagement letter filed.
""",
    "Scope and change control": """
- Building scope: high-level archetype-appropriate scope statement labelled **Assumption**.
- Exclusions and owner-supplied allowances as open items.
- Distinguish project-scope change (owner decision) from service-scope change (engagement variation).
""",
    "Approvals and compliance": """
- Include the archetype due diligence checklist table from the overlay (every row status = Assumption).
- Planning pathway decision status: unknown — test CDC vs DA per archetype overlay.
- NSW authority tracker table (status Assumption): BASIX, principal certifier, DA/CDC, CC, LSL receipt, Sydney Water/utility, OC.
- File due diligence under `03-design/01-due-diligence/`; authority tracker under `00-brief-pmp/` or `04-authority/`.
- For non-NSW state: inline gap callout for BASIX/HOW/LSL equivalents — do not extend NSW silently.
""",
    "Programme and staging regime": """
- State the baseline 3-stage regime: Stage 1 (concept/schematic to DA/CDC), Stage 2 (design development), Stage 3 (construction documentation and delivery).
- Include the sub-milestone table (MANDATORY — see contract appendix).
- For multi-dwelling: detailed staged regime per archetype overlay, mapped back to baseline stages.
- **Assumption**: durations TBC — use seed typical ranges as Judgement only, labelled.
""",
    "Cost, programme and procurement posture": """
- HIA elemental / residential cost plan posture: contingency 5–10%, PC sums (kitchen/bath), owner-supplied items tracked separately.
- Budget status: **Assumption: not evidenced** — recommend owner confirm working budget ceiling.
- Head-builder procurement (MANDATORY for architect-PM):
  - Typically 2–3 invited builders (**Assumption** until engagement confirms).
  - Evaluation criteria agreed before tender close.
  - Non-price criteria assessed separately from price at the right stage.
  - Tender evaluation matrix to open under `05-procurement/`.
  - Single clear recommendation to owner with conflict disclosure where applicable.
- Missing artefacts: elemental cost plan, master programme, tender evaluation matrix.
""",
    "Consultant coordination": """
- Consultant appointment tracker starter table: discipline | appointed by | status (Assumption) | scope stage | next action.
- Minimum disciplines from archetype overlay.
- Responsibility matrix and advice register to open under `02-consultant/`.
- Map consultant fee stages to PMP programme stages.
""",
    "Risks, decisions and next actions": """
- Top 5–8 archetype-appropriate risks with owner, status Assumption, and next action.
- Open owner decisions with recommended default and due date (relative to mobilisation run date or "within 2 weeks").
- Registers to open: action, decision, risk, authority approvals, consultant appointment.
""",
    "Internal audit layer": """
- Separate bullet lists: Facts | Assumptions | Judgements | Recommendations (min 3 recommendations).
- Each Recommendation must include an owner ask and due date where the owner must act.
- Draft register rows table (ID, description, owner, status, due date, source, next action) for at least: planning pathway decision, owner brief capture, engagement letter gap, authority pathway, risk register open.
- Use mobilisation run date for due dates — never invent past calendar years.
- Workflow warnings: no engagement letter, no owner brief, planning pathway untested, unsorted `_inbox/`.
- Repeat mandatory seed paths under "Mandatory seeds consulted".
""",
}

# Architect-PM section briefs when project evidence is available (Create/Update evidence_grounded).
ARCHITECT_PM_EVIDENCE_GROUNDED_SECTION_BRIEFS: dict[str, str] = {
    "Evidence basis and document control": """
- Status: draft, review-only, not issued. Version v01 (superseded at save with draft artefact version).
- Source hierarchy: project evidence (listed below) → doctrine → seeds listed in seed_consulted.
- **Evidence on file:** list each mobilisation document in Sources with date/status.
- **Gaps:** list only what is genuinely absent (owner brief sign-off, geotech, certifier, budget, etc.).
- Evidence map table (MANDATORY): | Section | Evidence status | Ref |
- Document control: save under `00-brief-pmp/`; supersede with next version when evidence arrives.
- Decision register to open under `08-meetings-reporting/` (append-only per decision-discipline).
""",
    "Project overview": """
- State declared archetype, role, state, and mobilisation phase (**post-engagement** when engagement letter is executed in Sources).
- Ground owner names, site address, and dwelling type from Sources — do not label them Assumption when stated in evidence.
- Summarise project understanding from fee proposal where present (knockdown-rebuild, GFA, LGA, site constraints).
- **Assumption** only for construction budget and other gaps not in Sources.
""",
    "Architect-PM role and appointment": """
- Default role declaration table: Architect/PM (advisory) | Superintendent (no, unless appointed) | Certifier (no) | Contract administrator (per engagement).
- When engagement letter is in Sources: state engagement **executed/on file** with date; scope from letter — not "not yet filed".
- PI insurance: ground holder, period, limit from engagement letter when stated; certificate-on-request as next action only.
- Builder instruments: verification checklist (licence, HBCF/HOW, LSL, insurance, contract) — verify only, not held by architect-PM.
""",
    "Two-brief discipline": """
- **Engagement brief (on file when letter + fee proposal in Sources):** fee, scope, PMP, governance, reporting, procurement services.
- **Owner project brief:** draft from fee proposal project understanding — **pending owner formal sign-off** (not "not yet filed" for engagement brief).
- Examples: extra tender round = engagement variation; bigger kitchen = project brief + decision register.
""",
    "Governance and decisions": """
- RACI-style matrix: Owner decides | Architect-PM recommends | Consultants advise | Builder executes | Certifier certifies.
- Decision gates: planning pathway, scheme endorsement, builder award, contract signature, CC issue, PC/OC.
- Note from engagement letter: no owner commitment without written approval except routine consultant coordination within scope.
- All decisions append-only per decision-discipline; file under `08-meetings-reporting/`.
""",
    "Communications protocol": """
- Ground owner update cadence from engagement letter when stated (e.g. monthly progress reporting).
- Forums: owner update, consultant coordination, builder RFIs (post-award), authority/certifier route.
- Emergency contact route.
- Owner escalation format (MANDATORY — use for material decisions):
  1. What this means for you
  2. What we need from you (with due date)
  3. What's happened
  4. What's next
  5. Background (if needed)
- Give a clear recommendation in escalations — not an option bundle without a view.
""",
    "Fee, services and programme relationship": """
- Ground fee basis and staged milestones from engagement letter when in Sources.
- List engagement letter **service exclusions** explicitly (distinct from building scope exclusions).
- Surface fee proposal tender assumptions (invited builder count, single formal tender) and conflict disclosures in procurement section too.
- Owner/authority delay impact on fee/programme — extension mechanism from engagement letter or **Assumption** if silent.
""",
    "Scope and change control": """
- Building scope: draft from fee proposal project understanding where present — label **draft pending owner brief sign-off**.
- Exclusions and owner-supplied allowances as open items.
- Distinguish project-scope change (owner decision) from service-scope change (engagement variation).
""",
    "Approvals and compliance": """
- Include the archetype due diligence checklist table (Assumption until each item filed).
- Planning pathway: upgrade from fee proposal when stated (e.g. DA assumed, CDC not assumed); otherwise test CDC vs DA.
- NSW authority tracker table (status Assumption): BASIX, principal certifier, DA/CDC, CC, LSL receipt, Sydney Water/utility, OC.
- File due diligence under `03-design/01-due-diligence/`; authority tracker under `00-brief-pmp/` or `04-authority/`.
""",
    "Programme and staging regime": """
- State the baseline 3-stage regime: Stage 1 (concept/schematic to DA/CDC), Stage 2 (design development), Stage 3 (construction documentation and delivery).
- Include the sub-milestone table (MANDATORY — see contract appendix).
- Surface engagement letter programme targets (e.g. target DA lodgement date) when in Sources.
- **Assumption**: durations TBC unless evidenced — use seed typical ranges as Judgement only, labelled.
""",
    "Cost, programme and procurement posture": """
- HIA elemental / residential cost plan posture: contingency 5–10%, PC sums, owner-supplied items tracked separately.
- Budget status: **Assumption: not evidenced** unless Sources state a budget — recommend owner confirm working budget ceiling.
- Head-builder procurement (MANDATORY for architect-PM):
  - Ground invited builder count and tender rounds from fee proposal / engagement letter when stated.
  - Surface fee proposal **conflict disclosure** (related-party builders) before tender list lock.
  - Evaluation criteria agreed before tender close; tender evaluation matrix under `05-procurement/`.
  - Single clear recommendation to owner with conflict disclosure where applicable.
- Missing artefacts: elemental cost plan, master programme, tender evaluation matrix.
""",
    "Consultant coordination": """
- Consultant appointment tracker: mark Architect/PM as **appointed/executed** when engagement letter is in Sources.
- Other disciplines remain Assumption until appointed.
- Responsibility matrix and advice register to open under `02-consultant/`.
- Map consultant fee stages to PMP programme stages.
""",
    "Risks, decisions and next actions": """
- Top 5–8 archetype-appropriate risks with owner, status Assumption, and next action.
- Open owner decisions with recommended default and due date (relative to mobilisation run date or "within 2 weeks").
- Registers to open: action, decision, risk, authority approvals, consultant appointment.
""",
    "Internal audit layer": """
- Separate bullet lists: Facts | Assumptions | Judgements | Recommendations (min 3 recommendations).
- **Facts:** at least two concrete items from Sources (engagement executed, fee, PI, DA pathway, programme target).
- **Assumptions:** genuine gaps only — never cite owner/site as Assumption when in Sources.
- Each Recommendation must include an owner ask and due date where the owner must act.
- Draft register rows tied to specific sources (Stage 1 invoice, master programme, conflict declaration before tender).
- Workflow warnings: real gaps only — never "no engagement letter" when letter is in evidence_refs.
- Repeat mandatory seed paths under "Mandatory seeds consulted".
""",
}


def programme_submilestone_table(user_role: str) -> str:
    return PROGRAMME_SUBMILESTONE_TABLES.get(
        user_role,
        ARCHITECT_PM_PROGRAMME_SUBMILESTONE_TABLE,
    )


def _archetype_overlay_for_role(archetype: str, user_role: str, *, state: str) -> str:
    overlay = ARCHETYPE_OVERLAYS.get(archetype, "").strip()
    if user_role != "architect-pm":
        filtered: list[str] = []
        for line in overlay.splitlines():
            lowered = line.lower()
            if "builder procurement" in lowered or "invited builders" in lowered:
                continue
            filtered.append(line)
        overlay = "\n".join(filtered).strip()
    if state != "NSW":
        overlay = overlay.replace(
            "BASIX alteration trigger (NSW ≥ $50k)",
            f"Energy efficiency trigger ({state} — confirm local obligation, not BASIX)",
        )
        overlay = overlay.replace(
            "NSW BASIX applies",
            f"{state} energy efficiency obligations apply (not BASIX — confirm local instrument)",
        )
        overlay = overlay.replace("NSW approvals stack:", f"{state} approvals stack (confirm local):")
    return overlay


def _adapt_due_diligence_for_state(checklist: str, state: str) -> str:
    if state == "NSW" or not checklist:
        return checklist
    adapted = checklist
    replacements = {
        "BASIX alteration trigger (NSW ≥ $50k)": (
            f"Energy efficiency / sustainability trigger ({state} — confirm local obligation, not BASIX)"
        ),
        "BASIX trigger (Class 1a secondary)": (
            f"Energy efficiency trigger ({state} — confirm local obligation, not BASIX)"
        ),
        "Sydney Water sewer diagram / BOS": (
            f"Utility sewer / drainage diagram ({state} equivalent)"
        ),
        "Housing SEPP CDC eligibility test": (
            f"State planning code / CDC eligibility test ({state})"
        ),
    }
    for old, new in replacements.items():
        adapted = adapted.replace(old, new)
    return adapted


def _state_note(state: str) -> str:
    if state == "NSW":
        return (
            "State handling: NSW is the deep default. Use BASIX, HBCF/HOW, LSL receipt, "
            "Sydney Water, and NSW planning pathways as written in seeds."
        )
    return (
        f"State handling: state={state}. Seeds are NSW-deep-default. For every NSW-specific "
        "instrument (BASIX, HBCF/HOW, LSL, Sydney Water, planning portal), add an inline "
        f"**{state} gap callout** and ask the project lead to confirm the local equivalent. "
        "Do not silently extend NSW guidance."
    )


def _archetype_due_diligence_checklist(archetype: str, *, state: str = "NSW") -> str:
    raw = ARCHETYPE_DUE_DILIGENCE_CHECKLISTS.get(archetype, "").strip()
    return _adapt_due_diligence_for_state(raw, state)


def strip_due_diligence_contract_meta(text: str) -> str:
    """Remove greenfield-brief meta-instructions from a due diligence checklist block."""
    lines = [
        line
        for line in text.splitlines()
        if not line.strip().startswith("Include this table under **Approvals and compliance**")
    ]
    return "\n".join(lines).strip()


def _architect_pm_greenfield_brief(
    *,
    archetype: str,
    state: str,
    evidence_grounded: bool = False,
) -> str:
    archetype_overlay = _archetype_overlay_for_role(archetype, "architect-pm", state=state)
    due_diligence = _archetype_due_diligence_checklist(archetype, state=state)
    section_briefs = (
        ARCHITECT_PM_EVIDENCE_GROUNDED_SECTION_BRIEFS
        if evidence_grounded
        else ARCHITECT_PM_SECTION_BRIEFS
    )
    contract_header = (
        "## Evidence-grounded content contract (MUST follow)"
        if evidence_grounded
        else "## Greenfield content contract (platform_seeded — MUST follow)"
    )
    parts = [
        contract_header,
        _state_note(state),
        GREENFIELD_DATE_RULE.strip(),
        ROLE_ARCHITECT_PM_OVERLAY.strip(),
        archetype_overlay.strip(),
    ]
    if due_diligence:
        parts.extend(["", due_diligence])
    parts.extend(
        [
            "",
            programme_submilestone_table("architect-pm").strip(),
            "",
            AUTHORITY_TRACKER_TABLE.strip(),
            "",
        ]
    )
    if evidence_grounded:
        parts.extend(
            [
                "Upgrade factual project statements from Sources in evidence_refs.",
                "Do NOT label documents in Sources as missing, not yet filed, or pre-brief / pre-engagement.",
                "Keep **Assumption** rows only where evidence is genuinely silent.",
                "For each required ## section below, include ALL bullets. Use tables and checklists.",
                "Write plain formal Australian English — no filler.",
                "",
            ]
        )
    else:
        parts.extend(
            [
                "For each required ## section below, include ALL bullets. Use tables and checklists — not single generic paragraphs.",
                "Label unknown project values as **Assumption** but still include the framework/checklist.",
                "Write plain formal Australian English — no filler ('facilitate collaboration', 'ensure clarity').",
                "",
            ]
        )
    for heading, brief in section_briefs.items():
        parts.append(f"### Section: {heading}")
        parts.append(brief.strip())
        parts.append("")
    return "\n".join(parts)


def _mobilisation_greenfield_brief(
    *,
    archetype: str,
    user_role: str,
    state: str,
    evidence_grounded: bool = False,
) -> str:
    role_overlay = ROLE_OVERLAYS.get(user_role, "")
    archetype_overlay = _archetype_overlay_for_role(archetype, user_role, state=state)
    due_diligence = _archetype_due_diligence_checklist(archetype, state=state)
    section_briefs = BUILDER_SECTION_BRIEFS if user_role == "builder" else None
    contract_header = (
        "## Evidence-grounded content contract (MUST follow)"
        if evidence_grounded
        else "## Greenfield content contract (platform_seeded — MUST follow)"
    )
    parts = [
        contract_header,
        _state_note(state),
        GREENFIELD_DATE_RULE.strip(),
        role_overlay.strip(),
        archetype_overlay.strip(),
    ]
    if due_diligence:
        parts.extend(["", due_diligence])
    parts.extend(
        [
            "",
            programme_submilestone_table(user_role).strip(),
            "",
            AUTHORITY_TRACKER_TABLE.strip(),
        ]
    )
    if user_role == "builder":
        parts.extend(
            [
                "",
                SUBCONTRACTOR_REGISTER_STARTER.strip(),
                "",
                RISK_REGISTER_TABLE.strip(),
            ]
        )
    parts.extend(
        [
            "",
            "Populate every required ## section with archetype- and role-specific checklists,",
            "statutory instrument tables (status Assumption), programme sub-milestone table,",
            "cost/contingency posture, and at least 5 risks in table form with next actions.",
            "",
            "Internal audit layer must use labelled bullet lists (not ### subheadings),",
            "draft register rows, and workflow warnings.",
            "Never use architect-PM procurement language (invited builders) when user_role is builder.",
        ]
    )
    if evidence_grounded:
        parts.extend(
            [
                "",
                "Project evidence is in Sources — upgrade factual statements from evidence_refs.",
                "Do NOT label indexed documents as not yet filed or pre-brief / pre-engagement.",
            ]
        )
    if section_briefs:
        parts.extend(
            [
                "",
                "For each required ## section below, include ALL bullets. Use tables and checklists.",
                "",
            ]
        )
        for heading, brief in section_briefs.items():
            parts.append(f"### Section: {heading}")
            parts.append(brief.strip())
            parts.append("")
    return "\n".join(parts)


def _format_value(value: object) -> str:
    if value is None:
        return "TBC"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return f"{value:g}"
    if isinstance(value, list):
        return ", ".join(_format_value(item) for item in value if item is not None) or "TBC"
    if isinstance(value, dict):
        return ", ".join(
            f"{key}: {_format_value(item)}"
            for key, item in value.items()
            if item is not None
        ) or "TBC"
    text = str(value).strip()
    return text or "TBC"


def _section_refs(
    seed_section_refs: dict[str, tuple[str, ...]] | None,
    section_id: str,
) -> tuple[str, ...]:
    if not seed_section_refs:
        return ()
    return seed_section_refs.get(section_id, ())


def _contract_focus_line(
    section_id: str,
    *,
    work_type: str | None,
    work_scope: tuple[str, ...],
    refs: tuple[str, ...],
) -> str:
    if section_id == "snapshot":
        return (
            "use a compact metadata table for site, address, client, class/type/"
            "subclass, scale, budget, timeframe, procurement route, and evidence status"
        )
    if section_id == "scope-client-requirements":
        focus = (
            "cover class/type/subclass, selected work scope, client requirements, "
            "scale fields, budget basis, and project-specific assumptions"
        )
        if "fire_services" in work_scope:
            focus += "; keep fire-services scope precise rather than generic services prose"
        else:
            focus += "; for residential new work, include finishes, fixtures, wet areas, and owner selections from seeds where loaded"
        return focus
    if section_id == "compliance-approvals":
        focus = (
            "cover DtS/performance pathway, NCC/authority gates, essential safety measures, "
            "approval status, and seed-backed compliance references"
        )
        if "fire_services" in work_scope:
            as_refs = ", ".join(ref for ref in refs if "as-2419" in ref or "as-2941" in ref)
            focus += (
                "; cite AS 2419.1 hydrant systems and AS 2941 pumpsets"
                f" from {as_refs or 'the loaded AS standards seed sections'}"
            )
        return focus
    if section_id == "programme":
        return "cover key milestones, authority lead times, procurement gates, and staging assumptions"
    if section_id == "cost-budget":
        return "cover budget status, cost risks, contingency, allowances, and benchmark/seed limits"
    if section_id == "procurement-delivery":
        if work_type == "advisory":
            return "cover services, deliverables, exclusions, hold points, and review outputs"
        return "cover procurement route, consultant/builder inputs, tender/award gates, and delivery responsibilities"
    if section_id == "risks":
        return "show a condensed top-risk register only; full detail belongs in companion annexures"
    if section_id == "actions-decisions":
        return "show top open decisions/actions only with owner, status, due basis, and next action"
    return "cover only project-specific content supported by setup inputs or loaded seeds"


def _adaptive_greenfield_brief(
    *,
    archetype: str,
    user_role: str,
    state: str,
    building_class: str,
    work_type: str | None,
    subclasses: tuple[str, ...],
    scale: dict[str, Any],
    complexity: dict[str, str],
    work_scope: tuple[str, ...],
    risk_flags: tuple[RiskFlag, ...],
    section_weights: dict[str, float],
    seed_section_refs: dict[str, tuple[str, ...]] | None,
    user_provided_fields: dict[str, Any],
    target_words: int,
    draft_mode: str,
) -> str:
    work_scope_items = work_scope_items_for(work_type, work_scope)
    complexity_labels = complexity_option_labels(
        building_class=building_class,
        subclasses=subclasses,
        complexity=complexity,
    )
    section_lines: list[str] = []
    for section_id in PMP_SECTION_HEADINGS:
        weight = section_weights.get(section_id, 0.0)
        heading = heading_for_section_id(section_id, work_type=work_type)
        refs = _section_refs(seed_section_refs, section_id)
        ref_note = f" Loaded seed sections: {', '.join(refs)}." if refs else ""
        section_lines.append(
            f"- {heading} (~{int(weight * target_words)} words): "
            f"{_contract_focus_line(section_id, work_type=work_type, work_scope=work_scope, refs=refs)}."
            f"{ref_note}"
        )

    setup_rows = [
        f"- User provided project title: {_format_value(user_provided_fields.get('title'))}",
        f"- User provided state: {_format_value(state)}",
        f"- User provided role: {_format_value(user_role)}",
        f"- User provided taxonomy: class={building_class}, work_type={work_type or 'TBC'}, "
        f"subclasses={', '.join(subclasses) or 'TBC'}",
    ]
    for key, value in scale.items():
        setup_rows.append(f"- User provided scale - {key}: {_format_value(value)}")
    for label in complexity_labels.values():
        setup_rows.append(f"- User provided complexity - {label}")
    for key, value in user_provided_fields.items():
        if key in {"title"} or value in (None, "", [], {}):
            continue
        setup_rows.append(f"- User provided {key}: {_format_value(value)}")

    scope_rows = [
        f"- {item.label}: consultants {', '.join(item.consultants) or 'TBC'}"
        for item in work_scope_items
    ] or ["- No work-scope items selected; list expected consultants as Assumption."]
    risk_rows = [
        f"- {flag.severity.upper()}: {flag.title} - {flag.description}"
        for flag in risk_flags
    ] or ["- No derived risk flags; keep generic risks short and project-specific."]

    return "\n".join(
        [
            "## Adaptive taxonomy PMP content contract (MUST follow)",
            f"Draft mode: {draft_mode}. Primary PMP target: {target_words} words inside the 2-4 page band.",
            "Length discipline: budgets are guides. Spend up to a section budget where the project warrants it; cut generic prose before project-specific facts.",
            "Condensed registers: top ~8 risks and top ~8 actions/decisions only. Full registers are companion artifacts/annexures.",
            "Evidence discipline: User setup facts are **User provided**. Missing current-corpus facts are **Assumption** or **Not evidenced**. Do not write **Grounded** in platform_seeded drafts.",
            "No fallback: if a required seed section is missing, state the gap for confirmation; do not fill it from pretrained domain content.",
            "",
            "### Project taxonomy",
            f"- Building class: {building_class}",
            f"- Work type: {work_type or 'TBC'}",
            f"- Subclass scale summary: {', '.join(subclasses) or 'TBC'}; "
            + (", ".join(f"{key}={_format_value(value)}" for key, value in scale.items()) or "scale TBC"),
            f"- Legacy archetype fallback label: {archetype or 'none'}",
            "",
            "### User provided setup fields",
            *setup_rows,
            "",
            "### Selected work-scope items",
            *scope_rows,
            "",
            "### Derived risk flags",
            *risk_rows,
            "",
            "### Per-section word budgets and loaded seed sections",
            *section_lines,
        ]
    )


def build_greenfield_brief(
    *,
    archetype: str,
    user_role: str,
    state: str,
    draft_mode: str = "platform_seeded",
    building_class: str | None = None,
    work_type: str | None = None,
    subclasses: tuple[str, ...] = (),
    scale: dict[str, Any] | None = None,
    complexity: dict[str, str] | None = None,
    work_scope: tuple[str, ...] = (),
    risk_flags: tuple[RiskFlag, ...] = (),
    section_weights: dict[str, float] | None = None,
    seed_section_refs: dict[str, tuple[str, ...]] | None = None,
    user_provided_fields: dict[str, Any] | None = None,
    target_words: int | None = None,
) -> str:
    if building_class is not None and section_weights is not None and target_words is not None:
        return _adaptive_greenfield_brief(
            archetype=archetype,
            user_role=user_role,
            state=state,
            building_class=building_class,
            work_type=work_type,
            subclasses=subclasses,
            scale=scale or {},
            complexity=complexity or {},
            work_scope=work_scope,
            risk_flags=risk_flags,
            section_weights=section_weights,
            seed_section_refs=seed_section_refs,
            user_provided_fields=user_provided_fields or {},
            target_words=target_words,
            draft_mode=draft_mode,
        )
    evidence_grounded = draft_mode == "evidence_grounded"
    if user_role == "architect-pm":
        return _architect_pm_greenfield_brief(
            archetype=archetype,
            state=state,
            evidence_grounded=evidence_grounded,
        )
    return _mobilisation_greenfield_brief(
        archetype=archetype,
        user_role=user_role,
        state=state,
        evidence_grounded=evidence_grounded,
    )


# Minimum terms that must appear in platform_seeded drafts (case-insensitive).
GREENFIELD_QUALITY_MARKERS: dict[tuple[str, str], tuple[str, ...]] = {
    ("new-dwelling", "architect-pm"): (
        "basix",
        "due diligence",
        "dilapidation",
        "stage 1",
        "contingency",
        "hbcf",
        "principal certifier",
    ),
    ("renovation", "architect-pm"): (
        "latent",
        "dilapidation",
        "due diligence",
        "stage 1",
        "contingency",
    ),
    ("multi-dwelling", "architect-pm"): (
        "classification",
        "consent",
        "stage",
        "contingency",
    ),
    ("ancillary", "architect-pm"): (
        "class",
        "cdc",
        "stage 1",
    ),
    ("small-commercial", "architect-pm"): (
        "reduced",
        "volume one",
        "licence",
    ),
    ("new-dwelling", "owner-builder"): ("owner-builder", "permit", "contingency", "recommendation"),
    ("renovation", "owner-builder"): ("due diligence", "permit", "park-for-decision", "recommendation"),
    ("new-dwelling", "builder"): ("hbcf", "lsl", "stage", "recommendation"),
    ("renovation", "builder"): (
        "latent",
        "hbcf",
        "variation",
        "contingency",
        "eot",
        "recommendation",
    ),
    ("new-dwelling", "d-and-c"): ("design responsibility", "pi", "hbcf", "recommendation"),
}


def greenfield_quality_markers(*, archetype: str, user_role: str) -> tuple[str, ...]:
    specific = GREENFIELD_QUALITY_MARKERS.get(
        (archetype, user_role),
        ("recommendation", "assumption", "stage"),
    )
    if user_role == "architect-pm":
        merged: list[str] = []
        seen: set[str] = set()
        for marker in (*specific, *ARCHITECT_PM_COMMON_MARKERS):
            if marker not in seen:
                seen.add(marker)
                merged.append(marker)
        return tuple(merged)
    return specific


def greenfield_markers_missing(markdown: str, *, archetype: str, user_role: str) -> list[str]:
    haystack = markdown.lower()
    return [
        marker
        for marker in greenfield_quality_markers(archetype=archetype, user_role=user_role)
        if marker not in haystack
    ]


GREENFIELD_ROLE_ANTIPATTERNS: dict[str, tuple[str, ...]] = {
    "builder": (
        "invited builders",
        "2–3 invited",
        "2-3 invited",
        "builder procured",
    ),
    "owner-builder": (
        "invited builders",
        "2–3 invited",
        "2-3 invited",
        "builder procured",
    ),
    "d-and-c": (
        "invited builders",
        "2–3 invited",
        "2-3 invited",
        "builder procured",
    ),
}

BUILDER_TRADE_MARKERS: tuple[str, ...] = (
    "demolition",
    "plumbing",
    "electrical",
    "waterproofing",
    "structural",
)


def _markdown_section(markdown: str, heading: str) -> str:
    target = heading.strip().lower()
    lines = markdown.splitlines()
    collecting = False
    section_lines: list[str] = []
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


def greenfield_structure_violations(
    markdown: str,
    *,
    archetype: str,
    user_role: str,
) -> list[str]:
    """Return structural quality issues beyond keyword depth markers."""
    violations: list[str] = []
    lower = markdown.lower()

    for pattern in GREENFIELD_ROLE_ANTIPATTERNS.get(user_role, ()):
        if pattern.lower() in lower:
            violations.append(
                f"role antipattern for {user_role!r}: must not include {pattern!r}"
            )

    audit_section = _markdown_section(markdown, "Internal audit layer").lower()
    if audit_section and "### facts" in audit_section:
        violations.append(
            "Internal audit layer must use labelled bullet lists, not ### subheadings"
        )

    risks_section = _markdown_section(markdown, "Risks, decisions and next actions").lower()
    if risks_section:
        has_risk_table = "| risk |" in risks_section or "| --- |" in risks_section
        has_prose_risks = "### risks" in risks_section or risks_section.strip().startswith("1.")
        if has_prose_risks and not has_risk_table:
            violations.append(
                "Risks section must use a risk register table (Risk | Owner | Status | Next action | Due)"
            )

    if user_role == "builder":
        procurement = _markdown_section(
            markdown, "Procurement and subcontractor posture"
        ).lower()
        if procurement:
            trade_hits = sum(1 for trade in BUILDER_TRADE_MARKERS if trade in procurement)
            if trade_hits < 3:
                violations.append(
                    "Procurement section must name at least 3 trades in the subcontractor register "
                    "(e.g. demolition, plumbing, electrical, waterproofing)"
                )
            if "| assumption | assumption | assumption | assumption | assumption |" in procurement:
                violations.append(
                    "Subcontractor register must use named trades — not 'Assumption' in every cell"
                )

        if archetype == "renovation" and "contingency" not in lower:
            violations.append(
                "Renovation builder draft must state contingency posture (5–10%) for latent conditions"
            )

    return violations
