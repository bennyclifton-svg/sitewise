# System skill: authority-approvals-system

**Job:** Maintain SiteWise approval pathway, authority tracker, consent-condition register and approval-related handoffs so statutory, certifier, utility and condition obligations remain visible from planning through handover.

This system inherits `../_shared/pm-contract.md`. It is the canonical SiteWise workflow for the framework alias `authority-approvals`.

## When to Use

Use this skill when:

- the user asks to identify, create, refresh, audit or explain project approvals;
- a project has DA, CDC, CC, building permit, BASIX, NatHERS, principal certifier, BPA, LSL, HBCF/HOW, Sydney Water, utility, OC or consent-condition uncertainty;
- tender, procurement, programme, variation, progress claim, PC, OC or handover work depends on an authority condition;
- a consent, approval, certificate, authority letter, certifier request, utility response or inspection result is added to the active project;
- an approval date, utility lead time or condition responsibility is being used in a programme or recommendation.

This skill controls approval records and drafts recommendations. It does not lodge applications, issue statutory certificates, act as certifier, give legal advice, or certify compliance.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Mode** - `pathway-summary`, `open-tracker`, `refresh-tracker`, `conditions-register`, `authority-gap-report`, `lead-time-review`, `handover-approval-check`, or `tender-condition-check`. Defaults to `refresh-tracker` where an authority tracker exists, otherwise `open-tracker`.
- **Subject focus** - optional, e.g. `DA conditions`, `CC prerequisites`, `utility lead times`, `BASIX final`, `Sydney Water`, `OC blockers`.
- **Current approval artefact path** - optional; if omitted, discover approval evidence in the active project.
- **Destination format** - `markdown`, `excel`, or `markdown-then-excel`. Defaults to markdown unless project evidence shows an Excel tracker is the accepted register source of truth.
- **Review date** - optional. Defaults to today's ISO date.

The skill reads project evidence only from the active project folder.

## Output Location

| Output | Default path |
| --- | --- |
| Authority approvals tracker | `04-planning-and-authorities/authority-approvals-tracker.md` or existing tracker workbook |
| Consent conditions register | `04-planning-and-authorities/consent-conditions-register.md` or existing register workbook |
| Utility approvals tracker | `04-planning-and-authorities/utility-approvals-tracker.md` |
| Approval pathway summary | `04-planning-and-authorities/approval-pathway-summary-vNN.md` |
| Authority gap report | `04-planning-and-authorities/authority-gap-report-vNN.md` |
| Tender condition check | `05-procurement/authority-condition-check-vNN.md` |
| Programme lead-time note | `06-programme/authority-lead-time-note-vNN.md` |
| Handover approval check | `09-handover-dlp/handover-approval-check-vNN.md` |
| Owner-facing approval summary | `08-meetings-reporting/owner-approval-summary-vNN.md` |

All markdown outputs go through `../atomic/markdown-draft-for-review.md`. Authority, consent-condition, utility, action, risk and decision rows go through `../atomic/register-row-draft.md`. Excel tracker edits go through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` after an approved markdown update plan.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before any authority approvals work:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration.
4. Do not load seeds, run evidence-sweep, inspect another project folder, draft tracker rows, extract conditions or draft approval commentary until the gate passes.

## Sequence

### Step 1 - Seed Targeted Read

Invoke `../atomic/seed-targeted-read.md` with task subject `authority approvals: <mode or subject focus>`.

Load:

- Tier 2 archetype seed per `archetype:`;
- Tier 3 role overlay per `user_role:`;
- `../../01-seed/setup-and-commission-guide.md` - required for statutory instrument pack and ready-to-start gates;
- `../../01-seed/sustainability-energy-guide.md` - required where BASIX, NatHERS, energy compliance, thermal comfort, hot water, PV, glazing or OC evidence is live;
- `../../01-seed/program-scheduling-guide.md` - required where approval, certifier or utility timing affects dates;
- `../../01-seed/contract-administration-guide.md` where approvals affect contract award, notices, EOT, claims, PC, OC, DLP or formal correspondence;
- `../../01-seed/procurement-quoting-guide.md` where consent conditions, BASIX commitments, management plans or authority prerequisites must flow into tender or subcontract scopes;
- `../../01-seed/cost-management-principles.md` where authority charges, contributions, utility costs, redesign or delay costs affect budget or contingency;
- topic or trade seeds where a specific condition affects a trade hold point, e.g. stormwater, waterproofing, fire separation, energy, structural or landscaping.

For non-NSW states, use only explicit state callouts in the loaded seeds and active-project evidence. If a loaded seed gives NSW-only guidance and no state callout covers the task, flag a state coverage gap and draft an action to confirm the local equivalent with the certifier, authority or project lead. Do not silently translate NSW DA/CDC/CC/BASIX/HBCF/HOW/LSL pathways into another state.

### Step 2 - Evidence Sweep

Invoke `../atomic/evidence-sweep.md` with task subject `authority approvals: <mode or subject focus>`.

High-relevance evidence:

- `README.md` for overlays, planning pathway, phase, project status and state;
- `00-brief-pmp/` for PMP, role declaration, owner project brief, authority assumptions and setup gaps;
- `01-cost/` for authority fees, contributions, allowances, contingency and approval-related budget exposure;
- `02-consultant/` for certifier, BASIX/NatHERS assessor, surveyor, structural, hydraulic, fire, access, landscape, traffic, heritage and authority-support appointments or advice;
- `03-design/` for drawings, specifications, design revisions, schedules and certifier submissions;
- `04-planning-and-authorities/` for DA, CDC, CC, building permit, BASIX/NatHERS, certifier appointment, LSL, HBCF/HOW, Sydney Water, OSD, public-domain, driveway/crossover, tree, heritage, utility approvals, authority correspondence, inspection schedules and consent conditions;
- `05-procurement/` for tender packs, subcontract scopes, long-lead orders, management plans and authority-condition flow-down;
- `06-programme/` for authority, certifier and utility lead times, milestone dates and approval blockers;
- `07-construction/` for inspection records, RFIs, notices, variations, EOTs, claims, site reports and certificates;
- `08-meetings-reporting/` for owner decisions, minutes, action register, risk register, escalation notes and reports;
- `09-handover-dlp/` for PC, OC, BASIX/NatHERS final evidence, warranties, manuals, certificates and handover blockers.

The sweep returns an evidence inventory and a gap report. Gaps become tracker rows, consent-condition rows, action rows, risk rows, decision requests or escalations depending on what they block.

### Step 3 - Resolve Approval Pathway and Register Substrate

Determine, from active-project evidence:

- planning pathway: exempt, DA, CDC, staged DA/CC, building permit or state equivalent;
- approval status: not-started, preparing, lodged, under-assessment, issued, conditional, refused, superseded, not-applicable or gap-report;
- principal certifier / building surveyor appointment status;
- whether the project has a markdown tracker, Excel tracker or no tracker yet;
- whether any tracker is reviewed/approved and therefore the working source, or draft/superseded and evidence only.

If the pathway is unknown or evidenced only by conversation, draft an authority gap report and action row. Do not choose a pathway from project name, address, budget or general knowledge.

If Excel is the working source, do not edit it directly. Draft a markdown update plan first, then use `excel-safe-edit` and `excel-verify` only after human approval.

### Step 4 - Build or Refresh the Authority Approvals Tracker

The authority approvals tracker records every approval, certificate, lodgement, authority response or statutory instrument that can block planning, procurement, construction, inspection, PC, OC or handover.

Reference tracker schema:

```markdown
| ID | Instrument / approval | Authority | Owner | Status | Due / review date | Source | Next action | Application reference | Date lodged | Date issued | Conditions reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

Draft each row through `../atomic/register-row-draft.md` as register type `Authority approvals tracker`. Every row must have a source reference. Where an approval source is not found, the source is the evidence-sweep gap report for this run and the row status is `gap-report`. Where evidence is found, use the closest recognised status such as `lodged`, `under-assessment`, `issued`, `conditional`, `refused`, `not-applicable` or `superseded`.

Minimum tracker topics to test:

| Topic | Typical row treatment |
| --- | --- |
| Planning pathway | DA, CDC, exempt, staged approval, building permit or state equivalent with source and status. |
| DA / CDC / consent | Approval reference, issue date, conditions reference and superseded status if amended. |
| Construction Certificate / building permit | Certifier, prerequisites, lodged / issued status and conditions. |
| Principal certifier / building surveyor | Appointment evidence, inspection schedule and communication route. |
| BASIX / NatHERS / energy | Current certificate/report, drawing/spec alignment, final certificate or OC evidence path. |
| LSL / state equivalent | NSW LSL receipt or explicit non-NSW gap/equivalent action. |
| HBCF / HOW / DBI / state equivalent | Role-appropriate evidence or not-applicable basis. |
| Sydney Water / water authority | Build Over Sewer, Section 73, connection, metering or equivalent where triggered. |
| Utilities | Water, sewer, electricity, gas, NBN/comms, meter upgrades, disconnections, reconnections and lead times. |
| OSD / stormwater / civil | OSD certificate, drainage approval, flood, civil, driveway/crossover, public-domain works. |
| Tree / heritage / environmental | Tree permit, heritage approval, contamination, erosion/sediment or council management conditions. |
| Management plans | CMP, WMP, TMP, dilapidation, acoustic, dust, traffic or site-specific authority plans. |
| Inspections and hold points | Certifier/BPA inspection schedule and evidence required before concealment or OC. |
| OC / final approvals | OC, final inspection, BASIX/NatHERS final evidence, structural certificates and authority close-out. |

Role-specific statutory inventory from `contract-setup-system.md` remains the setup opening pattern. This skill owns ongoing refresh, condition extraction, lead-time review and handoff after commissioning.

### Step 5 - Extract and Maintain the Consent Conditions Register

For each approval, determination, CDC, CC, permit, utility approval or authority letter with conditions:

1. Identify each condition that affects design, tender, procurement, construction method, inspection, management plans, completion, OC, operation, maintenance, handover or future owner obligations.
2. Draft one row per condition through `../atomic/register-row-draft.md` as register type `Consent conditions register`.
3. Link each row to the source approval and condition number.
4. Assign a responsible party from project evidence or role overlay. If responsibility is not evidenced, label the responsibility as Judgement or Assumption and surface for confirmation.
5. Assign a required-by stage: tender, before CC, before site start, before demolition, before excavation, before covering, before PC, before OC, before handover, during DLP, or ongoing.
6. Record the compliance evidence required to close the condition.

Reference consent conditions schema:

```markdown
| ID | Condition number | Source approval | Requirement | Required by stage | Responsible party | Status | Due / review date | Source | Evidence required | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

Do not leave conditions buried in a PDF or determination letter. Conditions that affect cost, time, scope, quality, compliance, procurement, access or owner decisions must also produce the relevant action, risk, decision, tender, programme or handover row.

### Step 6 - Review Authority, Certifier and Utility Lead Times

For each approval, response, inspection or connection that affects sequence:

- use active-project evidence first: lodged dates, authority response dates, certifier advice, utility correspondence, meeting decisions and current programme;
- use seed guidance only as contextual support and label unsupported durations as Assumption;
- include contingency where a duration is not evidenced;
- do not rely on best-case approval or utility durations;
- call `programme-system.md` where approval timing changes milestones, critical path, lookahead or delay records.

Draft a `06-programme/authority-lead-time-note-vNN.md` where dates are uncertain or programme assumptions need review. If a delay responsibility label is needed, use the responsibility labelling discipline from `programme-system.md`; do not assert authority delay as fact unless records prove it.

### Step 7 - Role and Archetype Shaping

Apply the declared overlays:

| Declaration | Authority approvals treatment |
| --- | --- |
| `user_role: owner-builder` | Track owner-builder permit, permit basis, principal certifier, trade contractor HBCF where triggered, renovation due diligence, trade licence checks and future-buyer warranty reminders. Do not create owner-builder HBCF/HOW rows for the owner's own work as outstanding gaps. |
| `user_role: architect-pm` | Track architect-PM role boundary and builder evidence verification separately. The architect-PM verifies builder HBCF/HOW, LSL, licence, insurance, BASIX/CC and authority prerequisites; the architect-PM does not hold or lodge builder instruments unless project evidence says they are separately engaged for that task. |
| `user_role: builder` | Track builder licence, Qualified Supervisor, HBCF/HOW, LSL, insurances, CC, BASIX/NatHERS, authority prerequisites, certifier inspections and utility applications as site-start, claim, PC or OC gates. |
| `user_role: d-and-c` | Include builder pack plus design responsibility, design deliverables, consultant PI, D&C PI, certifier submission protocol, construction-release dependencies and PPR/owner review status where authority or certifier submissions depend on design. |
| `archetype: renovation` | Test existing-condition, hazardous material, heritage, live occupancy, services, structural opening-up, neighbour/dilapidation and alteration/addition BASIX/NatHERS triggers. |
| `archetype: multi-dwelling` | Test NCC classification, party-wall/fire separation, separate metering, OSD/stormwater, infrastructure contributions, public-domain works, staged OC, subdivision/strata, per-dwelling handover and common-property obligations. |
| `archetype: ancillary` or `small-commercial` | Test whether residential assumptions are insufficient and flag the local authority/certifier confirmation needed for non-standard pathway, classification, approvals or handover evidence. |

### Step 8 - State Coverage Gap Handling

For `state: NSW`, use NSW seed guidance only where active-project evidence is missing, and label unsupported points as Assumption.

For non-NSW states:

- keep `state:` as a required declaration;
- use explicit callouts in the loaded seeds, e.g. VIC DBI/CoINVEST/NatHERS callouts where present;
- where no callout exists, draft a state-coverage gap row with owner, due date, source and next action;
- avoid NSW labels in output headings unless the active project evidence uses them;
- ask the project lead to supplement the local equivalent rather than inventing it.

Reference gap row:

```markdown
| AA-<TBD> | Confirm state equivalent for NSW <instrument> | Local authority / certifier | Project lead | gap-report | <review date> | Evidence-sweep gap report <date> | Confirm applicable state instrument and file source evidence before relying on the pathway |  |  |  |  |
```

### Step 9 - Cross-Control Handoffs

Approval rows are not passive records. For each material approval or condition, test whether it must be carried into:

| Control | Handoff |
| --- | --- |
| Tender / procurement | Include conditions, BASIX/NatHERS commitments, management plans, hold points, access limits, working hours, protection, utility prerequisites and close-out evidence in RFT/scopes. |
| Programme | Include approval, certifier, utility, inspection, OC and handover lead times with contingency and source references. |
| Cost | Record authority fees, contributions, redesign, compliance upgrades, management plans, utility charges, delay exposure or provisional assumptions. |
| Design | Record drawing/spec changes, BASIX/NatHERS alignment, certifier comments, consultant deliverables and design responsibility. |
| Delivery | Record site-start prerequisites, inspection hold points, management plans, evidence photos, certificates and authority correspondence. |
| Variation / RFI | Route authority-driven scope/compliance changes through `variation-management-system.md` or RFI controls where contract effect is live. |
| Handover | Carry BASIX/NatHERS final, OC, structural certificates, utility close-out, manuals, warranties and ongoing owner obligations to `handover-pc-system.md`. |
| Reporting | Surface blockers, stale assumptions and due owner decisions through action/risk/decision rows and owner-facing summaries. |

### Step 10 - Draft Outputs

For an approval pathway summary, include:

- frontmatter with `status: draft`, `seed_consulted`, `evidence_refs`, and folder-driven `voice_register`;
- declared overlays and state handling note;
- evidence basis and current pathway;
- authority approvals tracker excerpt;
- consent conditions register excerpt;
- utility / certifier lead-time table;
- approval prerequisites and blockers;
- non-NSW state gaps, if any;
- handoffs to tender, programme, cost, design, delivery and handover;
- action, risk, decision and escalation rows proposed;
- next review date.

For owner-facing summaries in `08-meetings-reporting/`, use stakeholder register: what this means, what is needed, by when, and what happens if it is late. Formal authority, certifier or contract correspondence uses contractual register.

### Step 11 - Excel Trackers

Where the project uses an Excel authority tracker or consent conditions register:

1. Inspect workbook metadata and visible sheet names where safe.
2. Draft a markdown update plan naming rows, columns, values, formulas and validations to change.
3. Obtain human approval for the update plan.
4. Use `../atomic/excel-safe-edit.md`.
5. Use `../atomic/excel-verify.md`.
6. If verification fails, report the workbook as not current and do not rely on the edit.

Do not create or modify `project.db`.

### Step 12 - Surface Gaps and Escalations

Escalate through `escalation-note-system.md` where:

- authority, certifier, utility or OC timing threatens critical path;
- an approval prerequisite blocks tender, award, site start, claim, PC, OC or handover;
- consent conditions are not extracted or have no owner;
- non-NSW state coverage is insufficient for the task;
- BASIX/NatHERS commitments conflict with drawings, specifications, procurement or installed work;
- LSL, HBCF/HOW/DBI, principal certifier, building permit, inspection or utility evidence is missing where the role/archetype/state requires it;
- responsibility for an authority condition is disputed or unevidenced;
- a formal notice, RFI, variation, EOT or owner decision is needed.

Also draft risk rows through `risk-register-system.md` and decision rows through `decision-record-system.md` where the approval pathway creates ongoing uncertainty or a project decision.

### Step 13 - Return Summary

Return:

- mode used;
- seeds loaded and `seed_consulted` list;
- evidence consulted;
- tracker/register substrate and output path(s);
- current approval pathway and status;
- approvals or conditions added/refreshed;
- lead-time assumptions and programme handoffs;
- tender, cost, design, delivery and handover handoffs;
- non-NSW state gaps;
- rows drafted for authority, consent-condition, utility, action, risk, decision or escalation controls;
- open gaps and next action.

## Rules / Must Not Do

- Do not bypass the Sec. 2 declaration gate.
- Do not read another project folder as evidence for the active project.
- Do not lodge applications, issue statutory certificates, certify compliance, approve conditions, or give legal advice.
- Do not rely on best-case authority, certifier or utility durations.
- Do not leave consent conditions buried in approvals, PDFs, correspondence or meeting notes.
- Do not treat NSW BASIX, DA/CDC/CC, HBCF/HOW or LSL guidance as applicable to a non-NSW project without an explicit callout or active-project evidence.
- Do not treat owner-builder HBCF/HOW for the owner's own work as an outstanding gap.
- Do not imply the architect-PM is the builder, certifier, Superintendent or statutory decision-maker unless the appointment evidence says so.
- Do not assert delay responsibility or condition responsibility as fact without source records.
- Do not edit Excel without `excel-safe-edit` and `excel-verify`.
- Do not write `project.db`.

## Fixture Checks

Use `../../99-docs/issues/sitewise-skills-framework-alignment/fixtures/authority-approvals/approval-tracker-row-fixture.md` as the SSFA-008 dry-run fixture.

Expected dry-run findings:

- the fixture creates authority approvals tracker rows with non-empty source references;
- DA/CDC/CC/BASIX/LSL/Sydney Water-style rows are sourced to fixture evidence or to the evidence-sweep gap report;
- pending CC and Sydney Water items are not given best-case issue dates;
- consent conditions are directed into the consent conditions register rather than left in the approval source;
- the fixture stays inside the issue-pack fixture and is not active-project evidence for unrelated projects.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/seed-targeted-read.md` - declaration gate and seed loading.
- `../atomic/evidence-sweep.md` - active-project evidence discovery.
- `../atomic/register-row-draft.md` - authority, consent-condition, utility, action, risk and decision rows.
- `../atomic/markdown-draft-for-review.md` - draft markdown wrapper and voice/folder discipline.
- `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` - controlled workbook update path.
- `../../00-doctrine/doctrine.md` planning-and-authorities section, evidence discipline, register discipline, state handling and escalation triggers.
- `../../01-seed/setup-and-commission-guide.md` - statutory instrument and ready-to-start baseline.
- `../../01-seed/sustainability-energy-guide.md` - BASIX, NatHERS and OC hold-point posture.
- `../../01-seed/program-scheduling-guide.md` - approval, certifier and utility timing posture.
- `contract-setup-system.md` - opens the initial statutory inventory at commissioning.
- `programme-system.md` - authority and utility lead-time handoff.
- `procurement-evaluation-system.md` - tender condition flow-down.
- `handover-pc-system.md` - PC, OC, BASIX/NatHERS final and handover evidence.
- `variation-management-system.md` - authority-driven variations, EOT support and formal notices.
- `escalation-note-system.md` - approval blockers and critical-path escalation.
