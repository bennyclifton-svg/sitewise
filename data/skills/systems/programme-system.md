# System skill: programme-system

**Job:** Establish, revise, and explain SiteWise residential programmes so baseline dates, milestones, critical path, lead times, lookaheads, delay records and linked impacts stay visible and reviewable.

This system inherits `../_shared/pm-contract.md`. It is the canonical SiteWise workflow for the framework alias `programme`.

## When to Use

Use this skill when:

- the user asks to create, baseline, update, revise or review a project programme;
- the user asks for a critical-path summary, milestone tracker, lookahead, programme risk commentary or programme variance summary;
- a workflow discovers missing or stale programme evidence;
- approval, utility, procurement, consultant, design, owner decision, site, handover, variation, claim or EOT evidence moves dates;
- a programme output is needed before cost planning, procurement, reporting, claim assessment, variation/EOT assessment or handover.

This skill creates programme controls and programme commentary. Clause-cited EOT notices and formal time-entitlement assessments remain with `variation-management-system.md` unless that system calls this one for programme evidence.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Mode** - `baseline-programme`, `revise-programme`, `milestone-tracker`, `lookahead`, `critical-path-summary`, `delay-register`, or `programme-risk-commentary`. Defaults to `baseline-programme` where no current programme exists, otherwise `revise-programme`.
- **Subject focus** - optional, e.g. `approval lead times`, `next six weeks`, `handover dates`, `window lead time`, `D&C design release`.
- **Current programme path** - optional; if omitted, discover programme artefacts in the active project.
- **Time horizon** - optional. Defaults: full lifecycle for master programme, next four to six weeks for lookahead, next eight weeks for milestone risk.
- **Revision date** - optional. Defaults to today's ISO date.
- **Destination format** - `markdown`, `excel`, or `markdown-then-excel`. Defaults to markdown unless project evidence shows Excel is the accepted programme source of truth.

The skill reads project evidence only from the active project folder.

## Output Location

| Output | Default path |
| --- | --- |
| Master programme draft | `06-programme/master-programme-vNN.md` |
| Programme workbook update plan | `06-programme/master-programme-vNN.update-plan.md` before `excel-safe-edit` |
| Milestone tracker | `06-programme/milestone-tracker.md` or existing tracker workbook |
| Lookahead | `06-programme/lookahead-vNN.md` |
| Critical-path summary | `06-programme/critical-path-summary-vNN.md` |
| Delay register | `06-programme/delay-register.md` or `07-construction/07-programme-eot/delay-register.md` where tied to EOT administration |
| Owner programme summary | `08-meetings-reporting/owner-programme-<topic>-vNN.md` |
| Programme risk commentary | `08-meetings-reporting/programme-risk-commentary-vNN.md` or `00-brief-pmp/programme-risk-commentary-vNN.md` |

All markdown outputs go through `../atomic/markdown-draft-for-review.md`. Programme, delay, action, decision, risk and EOT rows go through `../atomic/register-row-draft.md`. Excel programme edits go through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` after an approved markdown update plan.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before any programme work:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration.
4. Do not load seeds, run evidence-sweep, inspect another fixture folder, draft programme outputs or draft register rows until the gate passes.

## Sequence

### Step 1 - Seed Targeted Read

Invoke `../atomic/seed-targeted-read.md` with task subject `programme: <mode or subject focus>`.

Load:

- Tier 2 archetype seed per `archetype:`;
- Tier 3 role overlay per `user_role:`;
- `../../01-seed/program-scheduling-guide.md` - required;
- `../../01-seed/setup-and-commission-guide.md` - required for baseline commissioning milestones;
- `../../01-seed/contract-administration-guide.md` where EOT, notices, claims, stage payments, PC or DLP are live;
- `../../01-seed/cost-management-principles.md` where programme movement affects cashflow, contingency, claim timing or cost plan;
- `../../01-seed/procurement-quoting-guide.md` where procurement lead times, tender windows, award, subcontractor mobilisation or long-lead items are live;
- topic or trade seeds where activity-specific lead times or inspections require them.

For non-NSW states, carry the programme seed's graceful-degradation callout. Do not silently translate NSW CC, BASIX, HBCF/HOW or LSL timing into another state without project evidence.

### Step 2 - Evidence Sweep

Invoke `../atomic/evidence-sweep.md` with task subject `programme: <mode or subject focus>`.

High-relevance evidence:

- `README.md` for phase, overlays, planning pathway, budget and project status;
- `00-brief-pmp/` for PMP, scope, role declaration, owner decisions and setup gaps;
- `01-cost/` for cost plan, cashflow, PC sums, claim schedule, contingency and cost movement;
- `02-consultant/` for consultant appointments, deliverables and advice dates;
- `03-design/` for drawing revisions, design deliverables, design RFIs, design lock and certifier submissions;
- `04-planning-and-authorities/` for DA/CDC/CC/building permit, BASIX/NatHERS, consent conditions, utilities, LSL, HBCF/HOW, certifier and authority lead times;
- `05-procurement/` for tender windows, award dates, supplier commitments and subcontractor mobilisation;
- `06-programme/` for existing programmes, Gantt workbooks, milestone trackers, lookaheads and delay registers;
- `07-construction/` for claims, variations, EOTs, RFIs, site diaries, photos, inspection records, defects and handover blockers;
- `08-meetings-reporting/` for owner decisions, minutes, action register and reports;
- `09-handover-dlp/` for PC, OC, handover, DLP and defects dates.

If the active project has no current programme, record that as a gap and draft a baseline programme from evidence plus labelled assumptions. Do not invent certainty.

### Step 3 - Resolve Current Programme and Substrate

Find current programme artefacts in this order:

1. caller-provided programme path;
2. reviewed or approved programme workbook in `06-programme/`;
3. latest draft programme workbook in `06-programme/`;
4. latest markdown master programme or milestone tracker in `06-programme/`;
5. programme dates embedded in PMP, contract, claim schedule, procurement or handover evidence.

If more than one programme exists:

- identify the latest reviewed/approved version as the working baseline;
- treat draft or superseded programmes as evidence only;
- flag ambiguity where review status is unclear.

If Excel is the working source of truth, do not edit it directly. Draft a markdown update plan first, then route the approved edit through `excel-safe-edit` and `excel-verify`.

### Step 4 - Establish Baseline Calendar and Assumptions

Record:

- baseline date;
- revision date;
- calendar basis: calendar days or working days;
- working week, public holiday, industry shutdown and weather allowance assumptions;
- contract date obligations where evidenced;
- authority, certifier and utility lead-time assumptions;
- cycle-time assumptions from project evidence first, programme seed second;
- float / criticality assumptions.

Every unsupported duration or lead time is an Assumption. Every responsibility call is Judgement unless records prove responsibility.

Use Fact / Assumption / Judgement / Recommendation labels internally and in the hidden or commentary layer where uncertainty matters.

### Step 4A - Adopt the PMP Stage Regime

Before building or refreshing the milestone spine, read the latest current PMP in `00-brief-pmp/` where one exists and extract the high-level stage regime from the PMP programme / staging section, regardless of the section number used.

Rules:

- If the PMP programme / staging section defines a clear stage regime, use it as the programme phase spine.
- If no PMP exists, or the PMP programme / staging section is missing or vague, use the baseline stage regime as an explicit Assumption: Stage 1 - concept and schematic design to DA submission; Stage 2 - design development; Stage 3 - construction documentation and delivery.
- If programme evidence, authority evidence, consultant proposals or contract evidence suggests a more detailed or different stage regime, do not silently replace the PMP position. Record the variance, recommend updating the PMP, and show how the proposed programme maps back to the current PMP until that update is approved.
- If the programme is being updated after a PMP revision, reconcile any existing programme stage names and downstream procurement / consultant references that now drift.

### Step 5 - Build or Refresh the Residential Milestone Spine

At minimum, test whether the programme needs these milestones:

| Milestone | Notes |
| --- | --- |
| design lock | Starts approval, BASIX/NatHERS, structural and procurement chain. |
| planning approval / CDC / DA / building permit | Use declared state and project evidence. |
| CC or equivalent building approval | Include prerequisites such as LSL or state equivalent where applicable. |
| HBCF/HOW or state equivalent | Include where it blocks contract, money, start or claim posture. |
| site possession / commencement | Starts site risk and often contract time. |
| slab / footing inspection and pour | Stage-payment and inspection gate where relevant. |
| frame complete | Structural and claim milestone. |
| roof / lockup | Envelope and long-lead proof point. |
| rough-in complete | Services and lining gate. |
| fixing complete | Joinery, wet areas, finishes and services final path. |
| PC inspection / PC certificate | Completion and defects posture. |
| OC / occupancy approval | Authority close-out. |
| handover | Keys, manuals, warranties, certificates and final owner pack. |
| DLP start and end | Must tie to PC/handover evidence and defect notices. |

For `user_role: d-and-c`, add design responsibility, design deliverables, certifier submission and construction-release milestones. For `archetype: multi-dwelling`, add classification, party-wall/fire-separation, separate metering, infrastructure/OSD/stormwater, staged OC, subdivision/strata and per-dwelling handover milestones where relevant.

### Step 6 - Identify Critical and Near-Critical Paths

Identify:

- activities with no float or limited float;
- authority, certifier and utility lead times;
- long-lead procurement items;
- owner / Principal / self decisions blocking progress;
- consultant deliverables or design releases;
- inspection hold points;
- handover blockers including OC, BASIX/NatHERS final evidence, defects and manuals.

Criticality is a Judgement unless a reviewed CPM/Gantt programme or other project record proves the path.

### Step 7 - Link Programme Movement to Other Controls

For each material date movement, state the linked impact:

| Control | Programme link |
| --- | --- |
| Cost | preliminaries, escalation, contingency, cashflow, claim timing, PC sums, acceleration or resequencing. |
| Procurement | tender windows, award dates, long-lead order dates, supplier substitution, subcontractor mobilisation. |
| Authority | DA/CDC/CC/building permit, consent conditions, certifier inspections, utilities, OC/handover evidence. |
| Delivery | workface availability, trade stacking, weather, access, shutdown windows, inspections, defects and PC. |
| Risk | critical-path threats, stale assumptions, unowned decisions and lead-time exposure. |
| Decision | owner / Principal / self decisions needed to preserve or revise dates. |
| EOT / notice | potential time-entitlement pathway, handled by `variation-management-system.md` where clause-cited notice is required. |

Draft linked rows through `register-row-draft` and call `decision-record-system.md`, `risk-register-system.md`, `register-maintenance-system.md` or `escalation-note-system.md` where the movement requires those controls.

### Step 8 - Draft Programme Outputs

For a master programme draft, include:

- frontmatter with `status: draft`, `seed_consulted`, `evidence_refs`, `voice_register: contractual`;
- baseline / revision control;
- evidence basis;
- PMP stage regime and stage-alignment table;
- calendar assumptions;
- master programme table;
- milestone tracker;
- authority and utility lead-time table;
- long-lead procurement table;
- critical-path / near-critical summary;
- cycle-time annotation table;
- linked cost / procurement / authority / delivery impacts;
- risks, decisions and next actions;
- next programme review date.

Reference master programme table:

```markdown
| ID | Phase | Activity | Duration | Basis | Start / trigger | Finish / target | Dependency | Owner | Criticality | Source | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

For a milestone tracker:

```markdown
| Milestone | Baseline date | Current forecast | Movement | Movement basis | Criticality | Owner | Source | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

For a lookahead:

```markdown
| Week / date | Activity | Workface / location | Dependency | Constraint | Owner | Source | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
```

For a delay register:

```markdown
| ID | Event | Date noticed | Affected activity | Potential impact | Responsibility label | Evidence | Status | Owner | Due date | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

`Responsibility label` must be one of:

- `Fact - proven by record`;
- `Judgement - likely responsibility`;
- `Assumption - responsibility not evidenced`;
- `Not assessed`.

Do not use `owner delay`, `builder delay`, `authority delay`, `consultant delay`, `weather delay` or similar as a factual label unless the record proves it.

### Step 9 - Excel Programme Workbooks

Where the project uses a Gantt or programme workbook:

1. Inspect workbook metadata and visible sheet names where safe.
2. Draft a markdown update plan stating rows / columns / dates / formulas to change.
3. Obtain human approval for the update plan.
4. Use `../atomic/excel-safe-edit.md`.
5. Use `../atomic/excel-verify.md`.
6. If verification fails, report the workbook as not current and do not rely on the edit.

Do not recreate a Gantt workbook from scratch unless the user explicitly requests a new workbook and the output remains a draft.

For generated draft programme workbooks, the repeatable Gantt view is produced by the workbook exporter: keep the programme register as the auditable source sheet, add a relative-week `Gantt` sheet while baseline dates remain unset, and show uncertainty by using a solid bar for the minimum duration and a lighter extension for ranged durations. If a real baseline date is confirmed, the workbook can move from relative weeks to calendar dates through an approved update plan and `excel-safe-edit` / `excel-verify`.

### Step 10 - Surface Gaps and Escalations

Escalate through `escalation-note-system.md` where:

- critical path is threatened;
- authority, certifier or utility lead time is missing, stale or unrealistic;
- owner / Principal / self decision blocks programme;
- long-lead procurement is not ordered or not evidenced;
- programme movement affects cost, claim entitlement, EOT, PC, OC or handover;
- delay responsibility is being asserted without records;
- current programme conflicts with current project evidence;
- Excel verification fails.

Also draft risk rows through `risk-register-system.md` where time exposure remains open.

### Step 11 - Return Summary

Return:

- mode used;
- seeds loaded and `seed_consulted` list;
- evidence consulted;
- programme substrate and output path(s);
- baseline / revision date;
- current critical and near-critical paths;
- milestone movements;
- authority / utility / procurement lead-time assumptions;
- linked cost / procurement / authority / delivery impacts;
- rows drafted for action, decision, risk, delay or EOT support;
- open gaps and escalations;
- next review date.

## Rules / Must Not Do

- Do not bypass the Sec. 2 declaration gate.
- Do not read another project folder as evidence for the active project.
- Do not rely on optimistic dates without evidence.
- Do not omit authority, certifier or utility lead times where they affect sequence.
- Do not present delay responsibility as fact without supporting records.
- Do not treat HIA/MBA stage names as proof of physical completion.
- Do not hide programme movement as a reporting-only issue.
- Do not edit Excel without `excel-safe-edit` and `excel-verify`.
- Do not write `project.db`.
- Do not issue EOT notices, formal directions or contractual notices. Draft support only; human review and `variation-management-system.md` handle formal notices.

## Fixture Checks

Use `../../04-projects/0991-hydrant-sprinkler-head-upgrade/06-programme/` only as an SSFA-007 fixture path, not as active-project evidence for another project.

Fixture evidence:

- `draft_programme_v01.md` - Markdown programme with assumptions, phase durations, CDC / FRNSW / FER / procurement / delivery dependencies and watchpoints.
- `draft_programme_gantt_v01.xlsx` - workbook substrate; inspect and update only through Excel-safe workflow if a workbook edit is explicitly tested.

Expected dry-run findings:

- the fixture is acceptable as an example programme evidence set only when `0991-hydrant-sprinkler-head-upgrade` is the active project or when the issue pack is explicitly testing this system;
- the Markdown programme uses assumptions for CDC pathway, FRNSW review, FER update, shutdown constraints and long-lead items;
- the skill should preserve those as Assumption or Judgement until active-project records prove them;
- delay responsibility is not labelled as Fact because the fixture contains no contemporaneous delay record proving responsibility;
- the workbook is not edited by the fixture check.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/seed-targeted-read.md` - declaration gate and seed loading.
- `../atomic/evidence-sweep.md` - active-project evidence discovery.
- `../atomic/markdown-draft-for-review.md` - programme draft wrapper and voice/folder discipline.
- `../atomic/register-row-draft.md` - milestone, delay, action, decision, risk and EOT-support rows.
- `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` - controlled workbook update path.
- `../../00-doctrine/doctrine.md` programme section, evidence discipline, register discipline and escalation triggers.
- `../../01-seed/program-scheduling-guide.md` - residential programme and cycle-time posture.
- `../../01-seed/setup-and-commission-guide.md` - commissioning milestone baseline.
- `../../01-seed/contract-administration-guide.md` - EOT, notice, claim, PC and DLP context.
- `risk-register-system.md` - programme risk rows.
- `decision-record-system.md` - programme decisions and decision requests.
- `escalation-note-system.md` - critical-path and owner-decision escalations.
- `variation-management-system.md` - EOT notices and clause-cited time assessments.
