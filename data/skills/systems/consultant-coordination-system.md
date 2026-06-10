# System skill: consultant-coordination-system

**Job:** Maintain SiteWise consultant appointment, scope, deliverable, responsibility, advice and design-question controls so consultant input is complete, sourced, timely and carried into project decisions.

This system inherits `../_shared/pm-contract.md`. It is the canonical SiteWise workflow for the framework alias `consultant-coordination`.

## When to Use

Use this skill when:

- the user asks to set up, refresh, audit or explain consultant coordination;
- a project needs a consultant appointment tracker, responsibility matrix, deliverables schedule, advice register or design RFI register;
- a consultant proposal, appointment, fee variation, advice email, report, certificate, drawing issue or meeting note is added to the active project;
- a workflow discovers missing consultant scope, missing PI evidence, stale deliverables, verbally issued advice, late consultant input or unclear design responsibility;
- design, procurement, authority, programme, cost, variation, claim, RFI, PC, OC or handover work depends on consultant input.

This skill controls consultant coordination records and drafts recommendations. It does not appoint consultants, accept fee proposals, issue professional advice, certify designs or approve design responsibility transfers.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Mode** - `open-consultant-controls`, `refresh-consultant-controls`, `appointment-check`, `responsibility-matrix`, `deliverables-review`, `advice-register`, `design-rfi-sweep`, `scope-gap-report`, or `coordination-summary`. Defaults to `refresh-consultant-controls` where consultant controls exist, otherwise `open-consultant-controls`.
- **Subject focus** - optional, e.g. `structural appointment`, `BASIX coordination`, `certifier submission`, `D&C design responsibility`, `hydraulic Section 68`, `late deliverables`.
- **Target discipline** - required where the task is consultant procurement or RFP drafting. If omitted, build or refresh the appointment / status tracker first, then return discipline options before drafting; do not create or save a consultant RFP until one discipline has been selected.
- **Current consultant artefact path** - optional; if omitted, discover consultant evidence in the active project.
- **Destination format** - `markdown`, `excel`, or `markdown-then-excel`. Defaults to markdown unless project evidence shows an Excel tracker is the accepted register source of truth.
- **Review date** - optional. Defaults to today's ISO date.

The skill reads project evidence only from the active project folder.

## Output Location

| Output | Default path |
| --- | --- |
| Consultant appointment / status tracker | `02-consultant/consultant-appointment-tracker.md` or existing tracker workbook |
| Consultant responsibility matrix | `02-consultant/consultant-responsibility-matrix.md` or `03-design/design-responsibility-register.md` for D&C |
| Consultant deliverables schedule | `02-consultant/consultant-deliverables-schedule.md` or `03-design/design-deliverables-register.md` |
| Consultant advice register | `02-consultant/consultant-advice-register.md` |
| Design RFI register | `03-design/design-rfi-register.md` or `07-construction/08-rfi-notices/design-rfi-register.md` |
| Consultant scope gap report | `02-consultant/consultant-scope-gap-report-vNN.md` |
| Consultant coordination summary | `02-consultant/consultant-coordination-summary-vNN.md` |
| Consultant RFP / request for proposal (single discipline) | `02-consultant/consultant_procurement_<discipline>_vNN.draft.md`, e.g. `consultant_procurement_architect_v01.draft.md`, `consultant_procurement_structural_engineer_v01.draft.md` |
| Owner-facing consultant summary | `08-meetings-reporting/owner-consultant-summary-vNN.md` |

All markdown outputs go through `../atomic/markdown-draft-for-review.md`. Consultant appointment, advice, design responsibility, design deliverable, design RFI, action, risk and decision rows go through `../atomic/register-row-draft.md`. Excel tracker edits go through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` after an approved markdown update plan.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before any consultant coordination work:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration.
4. Do not load seeds, run evidence-sweep, inspect another project folder, draft consultant rows, infer missing disciplines or draft coordination commentary until the gate passes.

## Sequence

### Step 1 - Seed Targeted Read

Invoke `../atomic/seed-targeted-read.md` with task subject `consultant coordination: <mode or subject focus>`.

Load:

- Tier 2 archetype seed per `archetype:`;
- Tier 3 role overlay per `user_role:`;
- `../../01-seed/setup-and-commission-guide.md` - required for consultant controls opened at commissioning;
- `../../01-seed/procurement-quoting-guide.md` where consultant procurement, scope comparison, fee proposals, staged appointment or tender support is live;
- `../../01-seed/program-scheduling-guide.md` where consultant deliverables, design releases, certifier submissions or owner decisions affect dates;
- `../../01-seed/cost-management-principles.md` where consultant fees, exclusions, scope gaps or redesign affect budget and contingency;
- `../../01-seed/contract-administration-guide.md` where consultant advice affects formal RFIs, notices, variations, progress claims, PC, DLP or authority correspondence;
- `../../01-seed/sustainability-energy-guide.md` where BASIX, NatHERS, thermal comfort, glazing, insulation, hot water, PV or OC evidence is live;
- `../../01-seed/ncc-reference-guide.md` where NCC class, certifier pathway, performance solution, fire/access/acoustic or compliance responsibility is live;
- technical topic seeds where available and relevant, e.g. structural, MEP, civil, bushfire, trade interfaces or finishes.

For non-NSW states, use explicit state callouts in the loaded seeds and active-project evidence. If a loaded seed gives NSW-specific consultant, certifier, BASIX, NCC, HBCF/HOW or LSL posture without a local callout for the task, flag a state coverage gap and draft an action to confirm the local equivalent with the consultant, certifier or project lead.

### Step 2 - Evidence Sweep

Invoke `../atomic/evidence-sweep.md` with task subject `consultant coordination: <mode or subject focus>`.

High-relevance evidence:

- `README.md` for overlays, phase, planning pathway, NCC class, state and project status;
- `00-brief-pmp/` for PMP, role declaration, owner brief, engagement scope, governance map and owner decisions;
- `01-cost/` for cost plan, consultant fee allowances, fee proposals, cost reports and consultant-related variations;
- `02-consultant/` for consultant proposals, appointments, advice, reports, PI evidence, meeting notes, correspondence and coordination records;
- `03-design/` for drawings, specifications, discipline folders, design deliverables, design responsibility, design RFIs and revision status;
- `04-planning-and-authorities/` for authority requirements, certifier submissions, conditions, BASIX/NatHERS, CC/building permit, OC and authority correspondence;
- `02-consultant/` for consultant RFPs, appointment briefs, fee proposals, addenda and consultant appointment evidence;
- `05-procurement/` for builder tender qualifications and head-contractor procurement evidence that consultant scope must flow down into;
- `06-programme/` for consultant deliverable dates, design release milestones, certifier submission dates and late advice impacts;
- `07-construction/` for RFIs, variations, EOTs, claims, inspection records, site reports and consultant site observations;
- `08-meetings-reporting/` for minutes, action register, decision register, risk register and owner summaries;
- `09-handover-dlp/` for final certificates, warranties, as-builts, O&M material and consultant close-out evidence.

The sweep returns an evidence inventory and a gap report. Gaps become consultant appointment rows, responsibility rows, deliverable rows, advice rows, design RFIs, action rows, risk rows, decision requests or escalations depending on what they block.

### Step 3 - Resolve Consultant Team and Appointment Status

Build or refresh a consultant team map. Keep these categories separate:

| Category | Treatment |
| --- | --- |
| Lead consultant / architect | Record engagement scope, stage limits, deliverables, exclusions, authority to coordinate others and whether contract administration or Superintendent-like functions are included. |
| Specialist consultant | Record discipline-specific scope, deliverables, assumptions, exclusions, dependencies and whether they are owner-appointed, builder-appointed, D&C-appointed or novated. |
| Certifier / building surveyor | Record statutory role, independence, submission path and inspection requirements. Do not treat the certifier as designer. |
| Assessor / verifier | BASIX, NatHERS, bushfire, energy, access, acoustic or fire assessors: record assessment scope and evidence they must issue. |
| Cost consultant / QS | Record cost-report scope separately from design and contract-administration scope. |
| D&C design team | Record consultant appointments, novations, PI evidence, design responsibility, design deliverables and certifier submission obligations. |

Do not assume the lead consultant covers specialist advice. An architect's proposal does not cover structural, hydraulic, BASIX/NatHERS, geotechnical, bushfire, certifier, civil, survey, landscape, traffic, heritage, fire, access or acoustic scope unless the appointment evidence expressly says so.

The consultant appointment / status tracker is persistent project state, not a transient chat summary. Each run must re-read active-project evidence, reconcile the tracker, and identify stale or contradicted rows. The tracker is the control surface for "what do we procure next?", but the evidence remains the source of truth.

Use appointment statuses that are plain and evidence-based, for example: `engaged`, `proposal-received`, `proposal-issued`, `partial-scope`, `gap`, `not-required`, `unclear`, `complete`, or `superseded`. Do not mark a consultant engaged unless appointment or acceptance evidence exists.

Reference consultant appointment tracker schema:

```markdown
| ID | Consultant / firm | Discipline | Appointed by | Appointment status | Scope stage | PMP stage alignment | Fee basis | Key exclusions | Deliverables | Programme dependency | Source | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

Draft each appointment row through `../atomic/register-row-draft.md` as register type `Consultant appointment tracker`. Every row must have a source reference. If appointment evidence is missing, the source is the evidence-sweep gap report and the status is `gap`.

### Step 4 - Identify Required and Missing Disciplines

Test the required consultant set against declared overlays, planning pathway, NCC class and project evidence.

Common discipline prompts:

| Prompt | Typical triggers |
| --- | --- |
| Architect / designer | Any design-led residential project, DA/CDC/CC package, owner design decisions. |
| Structural engineer | New dwelling, renovation structural intervention, retaining, second storey, footing, large openings, steel, balconies. |
| Hydraulic / civil / stormwater | OSD, stormwater, sewer, AWTS, steep sites, pools, driveway, council infrastructure, multi-dwelling services. |
| Surveyor | Site levels, boundaries, easements, setout, subdivision, strata, existing conditions. |
| Geotechnical engineer | Sloping sites, excavation, retaining, reactive soils, rock, groundwater, underpinning, basements. |
| BASIX / NatHERS / energy assessor | New dwelling, alterations/additions trigger, glazing, insulation, hot water, PV, OC evidence. |
| Bushfire consultant | BAL, bushfire-prone land, AS 3959, RFS referral, APZ, shutters, vegetation. |
| Arborist / landscape | Trees, landscape conditions, protected vegetation, APZ planting, public-domain works. |
| Certifier / building surveyor | CC/building permit, inspections, OC, NCC compliance pathway. |
| Heritage / planning / town planner | Heritage, conservation area, DA complexity, planning pathway uncertainty. |
| Fire / access / acoustic | Multi-dwelling, Class 2, performance solutions, party walls, common areas, specialist compliance. |
| Quantity surveyor | Budget sensitivity, tender comparison, independent cost report, multi-dwelling or high-value custom work. |

Where a likely required discipline is absent, draft a scope-gap row and route to the action/risk/decision register as appropriate. A missing discipline is not neutral if it affects design, authority, cost, programme, procurement, construction release, PC, OC or handover.

### Step 4A - Consultant Procurement Discipline Selection and Stage Alignment

When the task is consultant procurement, request for proposal drafting, fee comparison or staged appointment:

1. Build or refresh the consultant appointment / status tracker from active-project evidence.
2. Identify disciplines already engaged, partially engaged, missing, unclear or complete.
3. If a target discipline was not passed by the caller, stop before drafting and return a short procurement choice list, for example: "Architect appears engaged for Stage 1 to 3; structural proposal received but not accepted; hydraulic proposal received but not accepted; civil status unclear. Which consultant package should be procured next?" This choice list is a preflight response, not the saved RFP artefact.
4. For the selected discipline, draft a single-discipline RFP only. The saved consultant procurement artefact must name the selected discipline and provide discipline-specific scope, deliverables, exclusions, returnables, fee-stage table, programme dependencies and evaluation criteria. Do not write a generic multi-discipline consultant procurement status artefact as the RFP.
4a. Save each discipline-specific RFP under `02-consultant/` with a discipline slug in the filename: `consultant_procurement_<discipline>_vNN.draft.md` (for example `consultant_procurement_architect_v01.draft.md`, `consultant_procurement_civil_engineer_v01.draft.md`). Version independently per discipline so multiple RFPs can coexist and be retrieved when issued together.
5. For the selected discipline, map the requested scope and fee stages to the PMP programme / staging regime. If that PMP staging is missing or vague, use the baseline stage regime as an Assumption and recommend a PMP update.
6. If an existing consultant proposal uses different stages, preserve those proposal stages as evidence but translate them into the PMP stage alignment table so the RFP, programme and fee comparison use one shared project language.
7. If the PMP, programme and consultant procurement artefact disagree on staging, recommend a coordinated update to align all three before issuing the RFP or accepting a fee proposal.

### Step 5 - Build or Refresh the Responsibility Matrix

Use the responsibility matrix when multiple parties touch one design element, authority submission, inspection, technical decision or deliverable.

Reference responsibility matrix schema:

```markdown
| ID | Element / issue | Lead responsibility | Specialist responsibility | Reviewer / certifier | Deliverable reference | Revision / status | Construction release dependency | Hold point | Source | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

Draft each row through `../atomic/register-row-draft.md` as register type `Design responsibility register`.

Responsibility rules:

- Lead consultant coordination responsibility is not specialist design responsibility.
- Certifier review is not design responsibility.
- Owner preference is not design responsibility unless the appointment or decision record says so.
- D&C design responsibility is allocated by contract/PPR/DRM evidence first, not by who drafted the latest drawing.
- Verbal allocation is not enough; capture it as an action or decision row until written evidence exists.

For `user_role: d-and-c`, responsibility matrix rows must include consultant appointment / novation source, consultant PI evidence where relied on, certifier submission requirement and construction-release dependency.

### Step 6 - Maintain Deliverables Schedule

For every consultant with active scope, identify:

- deliverable title and discipline;
- appointment source and scope stage;
- PMP stage alignment where a PMP exists or the baseline stage regime is being used as an Assumption;
- due date or programme dependency;
- issue purpose: advice, DA, CC, tender, IFC, construction observation, PC/OC close-out;
- current revision and status;
- reviewer / recipient;
- downstream dependency: authority submission, tender issue, procurement, construction release, inspection, claim, PC, OC or handover.

Reference deliverables schema:

```markdown
| ID | Consultant | Deliverable | Discipline | Issue purpose | Due / review date | Current status | Source | Dependency | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

Draft each row through `../atomic/register-row-draft.md` as register type `Design deliverables register` where the deliverable is design-side, or as an action row where the deliverable is a one-off consultant administration item.

Late or missing deliverables must be handed to `programme-system.md` when dates move, `risk-register-system.md` where exposure remains open, and `escalation-note-system.md` where an escalation trigger is hit.

### Step 7 - Maintain Consultant Advice Register

Any consultant input that affects cost, time, scope, quality, compliance, authority, procurement, construction release, PC, OC, handover, owner decision or contract entitlement becomes a consultant advice row.

Reference consultant advice schema:

```markdown
| ID | Consultant | Advice topic | Advice summary | Date received | Status | Owner | Due / review date | Source | Action taken | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

Draft each row through `../atomic/register-row-draft.md` as register type `Consultant advice register`.

Advice capture rules:

- Written advice uses the email, report, drawing, certificate or minute as source.
- Verbal advice is not treated as settled advice. Draft a confirmation email or action row naming who must confirm it and by when.
- Advice that changes scope, cost or time routes to `variation-management-system.md` or `decision-record-system.md` where owner / Principal sign-off is needed.
- Advice that affects authority or certifier pathway routes to `authority-approvals-system.md`.
- Advice that affects design quality, brief, budget, BASIX/NatHERS, NCC or options analysis routes to `design-review-evaluation-system.md`.

### Step 8 - Maintain Design RFIs and Open Questions

Where consultant evidence contains an unresolved question, missing input, request for information, conflicting advice, stale drawing, or certifier requirement:

1. Decide whether it belongs in the design RFI register, action register, consultant advice register or formal RFI register.
2. Draft the row through `register-row-draft`.
3. Assign one owner and one due date.
4. Link the affected deliverable, authority submission, programme activity, tender package or construction release.

Do not let open consultant questions remain buried in minutes, emails, fee proposals or internal notes.

Route any formal design RFI, construction RFI or response-tracking workflow to `rfi-management-system.md`.

### Step 9 - Role and Archetype Shaping

Apply the declared overlays:

| Declaration | Consultant coordination treatment |
| --- | --- |
| `user_role: owner-builder` | Keep consultant controls proportionate and plain. Track permit/certifier/design/advice gaps, trade contractor design input and owner decisions. Use the park-for-decision queue where the owner-builder defers a consultant decision. |
| `user_role: architect-pm` | Separate architect-PM engagement scope from owner project consultants. Track owner-appointed vs builder-appointed consultants, owner decisions, role authority, consultant advice, and owner-facing recommendations. Do not imply the architect-PM is certifier, builder, Superintendent or designer beyond the appointment evidence. |
| `user_role: builder` | Track consultant input needed to price, build, inspect, vary or claim: engineer instructions, certifier inspections, RFI responses, owner consultants and builder-side specialist advice. |
| `user_role: d-and-c` | Maintain DRM, consultant appointments/novations, consultant PI, D&C PI, deliverables, design RFIs, certifier submissions and construction-release dependencies. Design responsibility cannot drift by silence. |
| `archetype: renovation` | Test existing structure, hazardous material, services, live occupancy, heritage, moisture, termite, dilapidation, structural opening-up, waterproofing tie-ins and alteration/addition energy triggers. |
| `archetype: multi-dwelling` | Test classification, fire/acoustic/access, party wall, services metering, civil/stormwater/OSD, staged OC, strata/subdivision and common-property consultant responsibilities. |
| `archetype: ancillary` or `small-commercial` | Flag any consultant scope that falls outside residential default assumptions and route classification/authority questions to the certifier or project lead. |

### Step 10 - Cross-Control Handoffs

Consultant rows must be carried into the controls they affect:

| Control | Handoff |
| --- | --- |
| Authority approvals | Certifier submissions, BASIX/NatHERS, DA/CC/OC support, conditions, Section 68, Sydney Water, fire/access/acoustic/heritage advice. |
| Design review | Brief, options, budget, authority, compliance and quality implications of consultant advice. |
| Programme | Deliverable dates, late advice, review periods, certifier submission timing and construction-release dependencies. |
| Cost | Consultant fees, excluded services, redesign, fee variations, optional testing, specialist scope and contingency exposure. |
| Procurement | Consultant scope flow-down into RFTs, tender clarifications, builder qualifications, shop drawing review and technical schedules. |
| Variation / EOT / RFI | Consultant directions, responses, latent-condition advice, compliance changes and time impacts. |
| Handover | Structural certificates, BASIX/NatHERS final evidence, OC support, warranties, as-builts and close-out reports. |
| Reporting | Owner decisions, stale advice, late deliverables, missing discipline gaps and escalation triggers. |

### Step 11 - Draft Outputs

For a consultant coordination summary, include:

- frontmatter with `status: draft`, `seed_consulted`, `evidence_refs` and folder-driven `voice_register`;
- declared overlays and state handling note;
- current consultant team map;
- appointment tracker excerpt;
- responsibility matrix excerpt;
- deliverables schedule excerpt;
- advice register excerpt;
- design RFI / open question excerpt;
- missing disciplines and scope gaps;
- lead-consultant vs specialist-scope separation notes;
- cost, programme, authority, design, procurement and handover handoffs;
- action, risk, decision and escalation rows proposed;
- next review date.

Owner-facing summaries in `08-meetings-reporting/` use stakeholder register: what this means, what is needed, by when, and consequence if late. Consultant instructions, authority/certifier correspondence, formal RFIs and contract-linked advice use contractual register.

### Step 12 - Excel Trackers

Where the project uses an Excel consultant tracker, deliverables register or responsibility matrix:

1. Inspect workbook metadata and visible sheet names where safe.
2. Draft a markdown update plan naming rows, columns, values, formulas and validations to change.
3. Obtain human approval for the update plan.
4. Use `../atomic/excel-safe-edit.md`.
5. Use `../atomic/excel-verify.md`.
6. If verification fails, report the workbook as not current and do not rely on the edit.

Do not create or modify `project.db`.

### Step 13 - Surface Gaps and Escalations

Escalate through `escalation-note-system.md` where:

- a required discipline is missing or unappointed;
- lead-consultant scope is being assumed to include excluded specialist scope;
- a consultant deliverable is late or blocks authority, tender, construction release, inspection, PC, OC or handover;
- verbal advice affects cost, programme, scope, compliance, authority or owner decision and has not been confirmed;
- design responsibility, consultant PI, D&C PI, novation or certifier submission status is missing or stale;
- consultant advice conflicts with current project evidence, drawings, authority conditions, BASIX/NatHERS or the programme;
- an owner / Principal / self decision is required to appoint, extend, defer or replace consultant scope.

Also draft risk rows through `risk-register-system.md` and decision rows through `decision-record-system.md` where the consultant coordination issue creates ongoing uncertainty or a project decision.

### Step 14 - Return Summary

Return:

- mode used;
- seeds loaded and `seed_consulted` list;
- evidence consulted;
- tracker/register substrate and output path(s);
- consultant team status;
- appointments, responsibility rows, deliverables, advice rows or RFIs added/refreshed;
- lead-consultant vs specialist-scope separations;
- missing disciplines and scope gaps;
- cost, programme, authority, design, procurement and handover handoffs;
- rows drafted for consultant appointment, advice, design responsibility, deliverables, design RFI, action, risk, decision or escalation controls;
- open gaps and next action.

## Rules / Must Not Do

- Do not bypass the Sec. 2 declaration gate.
- Do not read another project folder as evidence for the active project.
- Do not appoint consultants, accept proposals, issue professional advice, certify designs or approve responsibility transfers.
- Do not assume the lead consultant covers specialist scope unless appointment evidence says so.
- Do not let client-side stakeholders direct consultants informally where the project lead is an intermediary.
- Do not treat verbal consultant advice as settled project advice without written confirmation.
- Do not let consultant deliverables drift without cost, programme, authority and design impact review.
- Do not imply the architect-PM is certifier, builder, Superintendent or designer beyond the appointment evidence.
- Do not treat the certifier as a designer or design reviewer beyond the statutory role evidenced.
- Do not let D&C design responsibility drift from the contract/PPR/DRM to whoever last touched a drawing.
- Do not edit Excel without `excel-safe-edit` and `excel-verify`.
- Do not write `project.db`.

## Fixture Checks

Use `../../99-docs/issues/sitewise-skills-framework-alignment/fixtures/consultant-coordination/bennett-consultant-fixture-check.md` as the SSFA-009 dry-run fixture.

Expected dry-run findings:

- the fixture uses `../../04-projects/0200-bennett-residence/02-consultant/` as issue-pack evidence only;
- architect DA-stage scope is separated from later CC/CA stages not authorised by the owners;
- structural and hydraulic proposals are identified as not accepted, not treated as appointments;
- energy assessor and bushfire consultant advice produces a responsibility row for BAL-FZ glazing, shutters and NatHERS/BASIX coordination;
- certifier advice is captured separately from design responsibility and routed to authority approvals;
- at least one consultant advice row and one design responsibility row include source references.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/seed-targeted-read.md` - declaration gate and seed loading.
- `../atomic/evidence-sweep.md` - active-project evidence discovery.
- `../atomic/register-row-draft.md` - consultant appointment, advice, design responsibility, deliverable, RFI, action, risk and decision rows.
- `../atomic/markdown-draft-for-review.md` - draft markdown wrapper and voice/folder discipline.
- `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` - controlled workbook update path.
- `../../00-doctrine/doctrine.md` consultant, design, authority, evidence, register, voice and escalation sections.
- `../../01-seed/setup-and-commission-guide.md` - consultant controls opened at setup.
- `../../01-seed/role-architect-pm.md` - architect-PM consultant and owner-advisory posture.
- `../../01-seed/role-d-and-c.md` - D&C consultant procurement, DRM and PI posture.
- `../../01-seed/program-scheduling-guide.md` - deliverable and certifier submission timing.
- `../../01-seed/procurement-quoting-guide.md` - consultant procurement and RFT flow-down.
- `authority-approvals-system.md` - authority and certifier pathway handoffs.
- `programme-system.md` - late deliverable and design release handoffs.
- `risk-register-system.md` - consultant scope, PI and missing-discipline risks.
- `decision-record-system.md` - owner / Principal appointment and scope decisions.
- `escalation-note-system.md` - missing discipline, late deliverable and verbal advice escalations.
