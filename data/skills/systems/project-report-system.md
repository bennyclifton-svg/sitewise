# System skill: project-report-system

**Job:** Produce recurring SiteWise project reports that reconcile time, cost, scope, quality and risk against current project controls, surface critical issues up front, and route decisions or contradictions to the right workflow.

This system inherits `../_shared/pm-contract.md`. It is the canonical SiteWise workflow for the framework alias `project-report`.

## When to Use

Use this skill when:

- the user asks for a monthly report, owner update, internal project report, status dashboard, exception report or project-control summary;
- time, cost, scope, quality and risk need to be reconciled into one report;
- a project lead needs a plain-English owner update with decisions and next actions;
- an internal or contractual report needs the current control position and escalation status;
- cost, programme, risk, authority, design, procurement, claims, variations, RFIs, defects or handover records contradict each other;
- a recurring report needs to confirm that figures and dates match the current registers.

This skill reports and reconciles the project position. It does not replace `cost-report-system.md`, `programme-system.md`, `risk-register-system.md`, `authority-approvals-system.md`, `variation-management-system.md`, `progress-claim-assessment-system.md` or `design-review-evaluation-system.md` when those workflows need to create or refresh source controls.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Mode** - `owner-monthly-update`, `internal-monthly-report`, `contractual-report`, `dashboard-summary`, `exception-report`, `board-pack`, or `report-quality-check`. Defaults to `owner-monthly-update` for architect-PM or owner-builder reports, otherwise `internal-monthly-report`.
- **Reporting period** - optional, e.g. `2026-06` or `May 2026`. Defaults to the current month if omitted.
- **Audience** - optional: owner, project lead, internal team, builder, contractor, consultant, lender, authority, or mixed.
- **Current registers** - optional paths to cost, programme, risk, action, decision, authority, variation, claim, RFI or defects registers.
- **Known focus** - optional, e.g. `budget pressure`, `DA status`, `critical path`, `owner decisions`, `construction delivery`, `handover blockers`.
- **Output path override** - optional.

The skill reads project evidence only from the active project folder.

## Output Location

| Output | Default path |
| --- | --- |
| Owner monthly update | `08-meetings-reporting/owner-update-YYYY-MM.md` |
| Internal monthly report | `08-meetings-reporting/project-report-YYYY-MM.md` |
| Contractual report | `08-meetings-reporting/contractual-project-report-YYYY-MM.md` or project-specified location |
| Dashboard summary | `08-meetings-reporting/dashboard-summary-YYYY-MM.md` |
| Exception report | `08-meetings-reporting/exception-report-<topic>-YYYY-MM.md` |
| Report quality check | `08-meetings-reporting/report-quality-check-YYYY-MM.md` |
| Owner decision pack from report | `08-meetings-reporting/owner-decision-pack-YYYY-MM.md` |

All markdown outputs go through `../atomic/markdown-draft-for-review.md`. Register, action, decision, risk and escalation rows go through `../atomic/register-row-draft.md`. Excel register edits, if any, go through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` only after a reviewed update plan.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before project reporting work:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration.
4. Confirm the reporting period and audience from caller input or project evidence.
5. Do not read another project folder, draft report outputs, or create register rows until the gate passes.

## Sequence

### Step 1 - Confirm Report Type and Voice

Classify the report before drafting:

| Mode | Audience | Voice | Front-page shape |
| --- | --- | --- | --- |
| `owner-monthly-update` | Residential owner / owner-builder future self | Stakeholder register | What this means for you, what we need from you, what changed, what is next |
| `internal-monthly-report` | Project lead / internal team | Contractual register | Executive summary, status table, exceptions, control reconciliation |
| `contractual-report` | Builder, contractor, consultant or formal governance forum | Contractual register | Executive summary, clause/source-aware status, notices and actions |
| `dashboard-summary` | Project lead / steering view | Contractual or stakeholder per audience | RAG status, top exceptions, decisions, next actions |
| `exception-report` | Decision-maker for a critical issue | Role-shaped per route | Trigger, impact, recommendation, decision needed |

Do not mix owner-facing stakeholder language and contractual notice language in the same section unless the report explicitly has separate audience sections.

### Step 2 - Seed Stance

Project reporting is normally register-led and does not require routine topic seed loading. Record `seed_consulted: []` when the report only summarises current evidence and registers.

Invoke `../atomic/seed-targeted-read.md` only when the report makes a new role-shaped recommendation, interprets an authority/compliance/contract risk, or turns missing evidence into a project-control judgement. In that case, load only the relevant seeds, such as:

- Tier 2 archetype seed per `archetype:`;
- Tier 3 role overlay per `user_role:`;
- `../../01-seed/cost-management-principles.md` for cost exposure, contingency, forecast or claim implications;
- `../../01-seed/program-scheduling-guide.md` for baseline, milestone, lead-time or critical-path implications;
- `../../01-seed/contract-administration-guide.md` for contractual report, variation, EOT, claim, RFI or notice implications;
- `../../01-seed/procurement-quoting-guide.md` for tender, award, long-lead or procurement issue reporting;
- `../../01-seed/sustainability-energy-guide.md` or `../../01-seed/ncc-reference-guide.md` for BASIX, NatHERS, NCC or compliance reporting;
- topic/trade seeds where a quality, defect, technical, handover or trade issue needs interpretation.

For non-NSW states, use explicit state callouts or active-project evidence. If a material state equivalent is missing, flag it as a report gap instead of assuming NSW.

### Step 3 - Evidence Sweep

Invoke `../atomic/evidence-sweep.md` with task subject `project report: <mode> <reporting period>`.

High-relevance evidence:

- `README.md` for project status, phase, overlays and declared constraints;
- `00-brief-pmp/` for PMP, project objectives, decision rights, owner priorities, baseline assumptions and known gaps;
- `01-cost/` for cost plan, budget tracker, QS reports, invoices, claims, variations, contingency and cost-risk commentary;
- `02-consultant/` for consultant appointments, deliverables, advice, late inputs and scope gaps;
- `03-design/` for design status, drawing revisions, design-risk view, design RFIs and unresolved design decisions;
- `04-planning-and-authorities/` for approval pathway, authority tracker, consent conditions, certifier advice, BASIX/NatHERS and utilities;
- `05-procurement/` for procurement status, tender actions, addenda, recommendation and award blockers;
- `06-programme/` for baseline programme, milestone tracker, lookahead, critical path and delay register;
- `07-construction/` for site records, progress claims, variations, EOTs, RFIs, quality, defects, inspections and notices;
- `08-meetings-reporting/` for previous reports, minutes, action register, decision register, risk register and owner updates;
- `09-handover-dlp/` for PC, OC, handover, warranties, defects and DLP blockers.

If a register or source control is absent, record that absence as a control gap. Do not fill it with a confident dashboard number.

### Step 4 - Resolve Current Control Sources

Build a current-controls table before drafting the report.

| Control | Preferred source | If missing |
| --- | --- | --- |
| Cost | Accepted cost plan, cost workbook, cost report, invoice/claim tracker, variation and contingency registers | Report "cost control gap"; use best available evidence only with Fact/Assumption labels |
| Programme | Approved baseline, current programme, milestone tracker, lookahead, delay register | Report "programme baseline gap"; do not present dates as certain |
| Scope | Brief, PMP, decision register, design review, variation register, procurement scope | Report unresolved scope decisions and route to `decision-record-system.md` |
| Quality/design | Design review, drawing register, RFI register, defects/inspection records, consultant advice | Report design/quality gap; route to `design-review-evaluation-system.md` or `rfi-management-system.md` |
| Risk | Risk register, escalation notes, authority tracker, consultant advice, PMP risk section | Report risk-register gap; route to `risk-register-system.md` |
| Authority | Approval tracker, planning note, consent conditions, certifier advice, utility records | Report approval-control gap; route to `authority-approvals-system.md` |
| Actions/decisions | Action register, minutes, decision register, owner update history | Report stale-action or decision gap; route to `decision-record-system.md` or `meeting-minutes-system.md` |

Source priority:

1. Reviewed/approved current register or workbook.
2. Current draft register or workbook.
3. Current system output with frontmatter and evidence references.
4. Source documents such as reports, certificates, claims, drawings, notices and minutes.
5. PMP or narrative summary.
6. Model judgement, only as labelled Judgement/Recommendation.

If two sources conflict, do not choose quietly. Create a `control contradiction` item on page one.

### Step 5 - Reconcile Headline Figures and Dates

Every reported figure, date and status must have:

- source path or register row;
- source status: reviewed, draft, current, superseded, unknown or gap;
- confidence: Fact, Assumption, Judgement or Recommendation;
- reconciliation note where another source differs.

Minimum reconciliation checks:

- Budget, forecast, committed, paid, pending variations and contingency do not contradict the current cost plan or cost workbook.
- Programme status does not contradict the current baseline, milestone tracker, authority tracker or lookahead.
- Scope status does not contradict the brief, decision register, design review or variation register.
- Quality status does not contradict drawing status, design reviews, RFIs, inspections or defects.
- Risk status does not omit high or critical risks from the current risk register or escalation notes.
- Authority status does not contradict planning pathway, certifier advice, consent conditions or utility records.

If reconciliation fails, the report must say so near the top. It may still be useful, but it cannot imply the controls are current.

### Step 6 - Build the Front Page First

The first page is the control surface. It must include:

1. Overall status in one sentence.
2. Top critical issues, normally three to five maximum.
3. Decisions needed this period.
4. What changed since the previous report, if a previous report exists.
5. Next actions and owners.
6. Control contradictions or missing source controls.

Critical risks are not appendix material. If an issue threatens budget, critical path, approval, safety, compliance, authority, insurability, construction release, PC/OC or owner decision timing, it belongs on page one.

Use RAG status only when each colour is supported by evidence. If evidence is missing, use `gap` instead of green/amber/red.

### Step 7 - Draft Dimension Sections

Keep the sections short and reconciled.

#### Time / programme

Report:

- baseline status;
- current forecast or milestone position;
- critical path or next eight-week risk;
- authority, utility, procurement, consultant or owner-decision date blockers;
- source path and register row.

Route missing or stale programme controls to `programme-system.md`.

#### Cost

Report:

- approved budget;
- current forecast;
- committed;
- paid;
- pending variations/claims;
- contingency status;
- top cost pressure and source.

Route stale cost plans to `cost-plan-system.md`. Route recurring detailed cost commentary to `cost-report-system.md`.

#### Scope

Report:

- approved scope baseline;
- open scope decisions;
- variations or pending changes;
- owner preference items that are not yet approved scope;
- procurement or construction release scope gaps.

Route decisions to `decision-record-system.md` and changes to `variation-management-system.md` where applicable.

#### Quality / design / compliance

Report:

- design status and current revision baseline;
- quality, defect, inspection or design-review issues;
- compliance and consultant coordination blockers;
- construction release or tender readiness risks.

Route design matters to `design-review-evaluation-system.md`, consultant matters to `consultant-coordination-system.md`, authority matters to `authority-approvals-system.md`, and RFIs to `rfi-management-system.md`.

#### Risk / authority / governance

Report:

- top risks by severity and next action;
- escalation triggers;
- authority and consent-condition status;
- overdue actions and decisions;
- governance gaps such as unclear role authority, missing contracts or missing insurance.

Route risk refreshes to `risk-register-system.md`, escalations to `escalation-note-system.md`, and register hygiene to `register-maintenance-system.md`.

### Step 8 - Owner-Facing Report Shape

For `owner-monthly-update`, use `../../00-doctrine/doctrine.md` owner-communication format:

1. What this means for you.
2. What we need from you.
3. What's happened.
4. What's next.
5. Background detail.

Rules:

- Do not lead with a table of technical risks.
- Do not bury the ask.
- Do not give three options without a recommendation unless evidence is missing.
- Keep the report short enough that an owner can act on it.
- Put dense register reconciliation in background detail or an internal appendix.

### Step 9 - Internal or Contractual Report Shape

For `internal-monthly-report`, `contractual-report` or `dashboard-summary`, use:

1. Executive summary.
2. Status dashboard with source references.
3. Critical exceptions and decisions.
4. Time.
5. Cost.
6. Scope/change.
7. Quality/design/compliance.
8. Risk/authority/governance.
9. Actions, decisions and escalations.
10. Source-control reconciliation.
11. Assumptions, gaps and contradictions.

For contractual reports, cite contract clauses or formal source records where the report speaks to entitlement, obligation, due dates, notices, claims, variations, EOTs, PC/OC, defects or handover.

### Step 10 - Create Handoffs

The report is not a dead end. Route issues:

- Critical risk -> `escalation-note-system.md`.
- Missing or stale register -> `register-maintenance-system.md`.
- Owner/project-lead decision -> `decision-record-system.md`.
- Cost pressure -> `cost-plan-system.md` or `cost-report-system.md`.
- Programme movement -> `programme-system.md`.
- Approval issue -> `authority-approvals-system.md`.
- Consultant deliverable/advice issue -> `consultant-coordination-system.md`.
- Design/quality issue -> `design-review-evaluation-system.md`.
- Payment claim issue -> `progress-claim-assessment-system.md`.
- Variation/EOT issue -> `variation-management-system.md`.
- RFI issue -> `rfi-management-system.md`.
- Minutes/action issue -> `meeting-minutes-system.md`.
- Handover/defects issue -> `handover-pc-system.md`.

Draft action, decision, risk or escalation rows through `../atomic/register-row-draft.md`; do not silently update controlled registers.

### Step 11 - Draft the Report

Every output is a draft for review.

Minimum frontmatter:

```yaml
---
status: draft
author: agent
date: YYYY-MM-DD
reporting_period: YYYY-MM
audience: owner | internal | contractual | mixed
seed_consulted: []
evidence_refs: []
source_controls: []
control_gaps: []
---
```

Minimum body:

1. Report purpose and limits.
2. Front-page status and critical issues.
3. Decisions needed.
4. Time, cost, scope, quality and risk sections.
5. Handoffs and next actions.
6. Source-control reconciliation.
7. Assumptions, gaps and contradictions.

### Step 12 - Quality Check

Before returning, score the draft against `../../99-docs/eval/document-quality-rubric.md` general document quality and hard-fail gates.

Hard-fail if the report:

- uses unsupported figures or dates as facts;
- uses evidence from another active project;
- ignores a material contradiction;
- hides material uncertainty;
- buries a critical risk;
- replaces project-specific reporting with generic doctrine;
- reports a figure that cannot be reconciled to a current source.

If the score is conditional or failed, create a specific improvement item in the output and in the return summary.

### Step 13 - Return Summary

Return:

- report draft path;
- reporting period and audience;
- top critical issues;
- decisions needed;
- source-control contradictions or gaps;
- handoffs created;
- rubric result;
- tests or fixture checks run.

## Guardrails

- Do not bypass the three-overlay declaration gate.
- Do not use another project's evidence.
- Do not report unsupported dashboard numbers.
- Do not present missing registers as "green".
- Do not bury critical risks in background detail or appendices.
- Do not mix owner-facing and contractual voice without clear section separation.
- Do not overwrite Excel registers or report workbooks without Excel-safe skills.
- Do not close actions, decisions, risks or register rows without evidence.
- Do not write to `project.db`.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/evidence-sweep.md` - active-project evidence sweep.
- `../atomic/markdown-draft-for-review.md` - draft markdown output discipline.
- `../atomic/register-row-draft.md` - action, decision, risk and escalation row drafting.
- `register-maintenance-system.md` - source-control and register hygiene.
- `risk-register-system.md` - risk refresh and risk commentary.
- `programme-system.md` - programme baseline, milestone and critical-path reporting.
- `cost-plan-system.md` - cost baseline and cost-plan refresh.
- `authority-approvals-system.md` - approval tracker and consent-condition reporting.
- `consultant-coordination-system.md` - consultant appointment, advice and deliverable gaps.
- `design-review-evaluation-system.md` - design-risk and design-status reporting.
- `escalation-note-system.md` - formal early-warning and escalation notes.
- `decision-record-system.md` - owner/project-lead decisions.
- `../../00-doctrine/doctrine.md` - voice, evidence, owner communication, register, decision and escalation discipline.
- `../../99-docs/eval/document-quality-rubric.md` - report quality checks.

## Fixture Check

Use `../../99-docs/issues/sitewise-skills-framework-alignment/fixtures/project-report/bennett-monthly-report-fixture-check.md` as the regression fixture. A passing review produces:

- a page-one critical issue view for APZ/DA, budget gap, missing baselines and consultant/design blockers;
- source-control reconciliation for cost, programme, scope, quality and risk;
- owner-facing decision prompts in stakeholder voice;
- a rubric scorecard with no hard-fail gates triggered.
