# System skill: cost-report-system

**Job:** Produce recurring SiteWise cost reports that reconcile approved budget, forecast, committed, paid, pending and contingency positions against current cost controls, then surface budget pressure early with source-backed actions.

This system inherits `../_shared/pm-contract.md`. It is the canonical SiteWise workflow for the framework alias `cost-report`.

## When to Use

Use this skill when:

- the user asks for a cost report, monthly cost report, cost dashboard, budget update, contingency report or budget-pressure summary;
- approved budget, forecast final cost, commitments, paid amounts, pending changes and contingency need to be shown together;
- invoices, contractor claims, consultant invoices, variations, quotes or internal forecasts need to be reconciled without blurring status;
- a cost plan, invoice tracker, progress-claim tracker, variation register or contingency register appears stale, incomplete or contradictory;
- a project report needs detailed cost commentary that `project-report-system.md` should not carry in full;
- budget pressure is likely and needs early escalation.

This skill reports the cost-control position. It does not certify payment, assess a contractor claim, approve a variation, create the baseline cost plan, or update an Excel workbook unless those workflows are explicitly invoked through their own controls.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Mode** - `monthly-cost-report`, `owner-cost-update`, `cost-dashboard`, `contingency-review`, `invoice-reconciliation`, `variation-cost-view`, `budget-pressure-warning`, or `cost-report-quality-check`. Defaults to `monthly-cost-report`.
- **Reporting period** - optional, e.g. `2026-06` or `May 2026`. Defaults to the current month if omitted.
- **Current cost plan or workbook path** - optional.
- **Invoice, claim, variation or contingency register paths** - optional.
- **Audience** - optional: owner, project lead, internal team, builder, contractor, lender, QS or mixed.
- **Known focus** - optional, e.g. `pool decision`, `contingency drawdown`, `pending variations`, `consultant invoices`, `QS forecast`, `builder claim`.
- **Output path override** - optional.

The skill reads project evidence only from the active project folder.

## Output Location

| Output | Default path |
| --- | --- |
| Monthly cost report | `01-cost/cost-report-YYYY-MM.md` |
| Cost dashboard | `01-cost/cost-dashboard-YYYY-MM.md` |
| Contingency review | `01-cost/contingency-review-YYYY-MM.md` |
| Invoice reconciliation note | `01-cost/invoice-reconciliation-YYYY-MM.md` |
| Variation cost view | `01-cost/variation-cost-view-YYYY-MM.md` or `07-construction/06-variations/variation-cost-view-YYYY-MM.md` |
| Budget-pressure warning | `01-cost/budget-pressure-warning-YYYY-MM.md` or `08-meetings-reporting/owner-cost-warning-YYYY-MM.md` |
| Owner cost update | `08-meetings-reporting/owner-cost-update-YYYY-MM.md` |
| Quality check | `01-cost/cost-report-quality-check-YYYY-MM.md` |

All markdown outputs go through `../atomic/markdown-draft-for-review.md`. Cost, invoice, claim, variation, contingency, action, decision, risk and escalation rows go through `../atomic/register-row-draft.md`. Excel edits go through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` only after a reviewed update plan.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before cost reporting work:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration.
4. Confirm reporting period, audience and whether the report is owner-facing or internal.
5. Do not read another project folder, draft cost-report outputs, or create register rows until the gate passes.

## Sequence

### Step 1 - Confirm Report Type and Voice

Classify the output:

| Mode | Audience | Voice | Shape |
| --- | --- | --- | --- |
| `monthly-cost-report` | Project lead / internal team | Contractual register | Executive cost summary, reconciliation table, risks, actions |
| `owner-cost-update` | Residential owner | Stakeholder register | What this means for you, what we need from you, current cost position, options |
| `cost-dashboard` | Project lead / dashboard | Contractual register | Source-backed status lanes and exceptions |
| `contingency-review` | Project lead / owner where decision needed | Contractual or stakeholder per audience | Contingency status, drawdown, commitments, decisions |
| `invoice-reconciliation` | Project lead / accounts / QS | Contractual register | Invoice source, allocation, paid status, tracker gaps |
| `variation-cost-view` | Project lead / contract admin | Contractual register | Approved, pending, rejected and forecast variation exposure |
| `budget-pressure-warning` | Decision-maker | Role-shaped escalation | Trigger, cause, amount, consequence, recommendation |

Do not mix owner-facing explanation with contractor-facing entitlement language unless the output has separate audience sections.

### Step 2 - Load Cost Knowledge Deliberately

Invoke `../atomic/seed-targeted-read.md` when the report makes a cost-control judgement, gives a recommendation, interprets contingency, or escalates budget pressure.

Load:

- Tier 2 archetype seed per `archetype:`;
- Tier 3 role overlay per `user_role:`;
- `../../01-seed/cost-management-principles.md` - required for cost-report judgement;
- `../../01-seed/contract-administration-guide.md` where claims, variations, EOT cost, notices or contract sums are live;
- `../../01-seed/procurement-quoting-guide.md` where quotes, tender returns, procurement route or contract form affect cost certainty;
- `../../01-seed/program-scheduling-guide.md` where preliminaries, escalation, delay or lead time affect cost;
- topic or trade seeds where the cost issue is technical, e.g. structural, civil, MEP, finishes, energy or defects.

Load `../reference/nsw-residential-cost-breakdown-reference.md` where the cost plan, invoice or variation evidence needs a residential taxonomy to organise cost items. Treat it as reference data only, not active-project evidence or market-rate advice.

For non-NSW states, use active-project evidence and explicit state callouts only. Do not silently translate NSW statutory cost lines to another state.

### Step 3 - Evidence Sweep

Invoke `../atomic/evidence-sweep.md` with task subject `cost report: <mode> <reporting period>`.

High-relevance evidence:

- `README.md` for overlays, phase, project status, budget metadata and project boundary;
- `00-brief-pmp/` for budget ceiling, owner decisions, PMP cost basis and known scope trade-offs;
- `01-cost/` for cost plans, QS reports, cost workbooks, invoice trackers, invoice source documents, contingency registers, budget notes and prior cost reports;
- `02-consultant/` for fee proposals, appointments, invoices, committed consultant scope and unaccepted mandatory cost items;
- `03-design/` for design changes, scope movement and design-risk items affecting cost;
- `04-planning-and-authorities/` for authority fees, consent conditions, certifier requirements, BASIX/NatHERS, utilities, LSL, HBCF/HOW and approval-driven cost risks;
- `05-procurement/` for quotes, tender returns, tender clarifications, award recommendations, contract sums and exclusions;
- `06-programme/` for escalation, preliminaries, cashflow, critical-path movement and time-related cost exposure;
- `07-construction/` for progress claims, contractor claims, variations, EOT cost impacts, site instructions, RFIs, defects, notices and claim schedules;
- `08-meetings-reporting/` for decisions, owner approvals, meeting actions, reports and budget-pressure escalations;
- `09-handover-dlp/` for final claims, defects, PC/OC conditions, warranties and DLP costs.

If a cost source control is absent, record it as a cost-control gap. Do not fill the gap with a confident figure.

### Step 4 - Resolve Cost Source Controls

Build a source-control table before drafting cost commentary.

| Control | Preferred source | If missing |
| --- | --- | --- |
| Approved budget | Reviewed cost plan, approved budget decision, contract sum or owner decision record | Report approved-budget gap; do not treat owner aspiration as approved budget |
| Forecast final cost | Current cost plan/workbook, QS report, approved contracts plus forecast variations and allowances | Report forecast gap; use best available evidence with status labels |
| Committed | Accepted appointments, signed contracts, POs, awarded packages, approved variations | Report commitment gap; do not treat issued proposals as committed |
| Paid | Invoice tracker, paid invoices, payment records, progress claim payment records | Report paid-position gap; do not treat claimed or invoiced as paid |
| Pending | Pending variations, pending claims, issued proposals awaiting decision, unresolved owner scope choices | Report pending exposure with decision owner |
| Contingency | Contingency register, cost plan contingency line, approved drawdown decisions | Report contingency-control gap; do not use contingency as scope money |
| Claims | Progress claim tracker and assessed claim notes | Route to `progress-claim-assessment-system.md` where assessment is needed |
| Variations | Variation register and variation assessment notes | Route to `variation-management-system.md` where entitlement or assessment is needed |

Source priority:

1. Reviewed/approved cost workbook or cost register.
2. Current draft cost workbook or cost plan.
3. Current QS/cost-manager report.
4. Accepted contract, appointment, PO, claim, invoice or variation source.
5. PMP or project report cost summary.
6. Benchmark taxonomy or model judgement, only as labelled Assumption/Judgement.

If sources conflict, create a `cost evidence conflict` item and keep both figures visible.

### Step 5 - Classify Every Cost Line by Status

Every line in the report must carry one clear status:

| Status | Meaning |
| --- | --- |
| `approved-budget` | Human-approved budget or reviewed cost-plan budget line |
| `forecast` | Expected cost exposure not yet committed |
| `committed` | Accepted appointment, signed contract, PO, awarded package or approved variation |
| `claimed` | Contractor or supplier has claimed; not necessarily assessed or paid |
| `assessed` | Claim/payment has been assessed by the responsible party |
| `paid` | Payment evidence exists |
| `pending` | Unapproved variation, unaccepted proposal, open owner decision or unresolved cost exposure |
| `contingency` | Contingency allowance or approved drawdown |
| `excluded` | Outside current cost report scope |
| `gap` | Source control missing or status cannot be proved |

Do not mix consultant invoices, contractor progress claims, supplier invoices and internal forecasts in one line unless the line separates status and source type.

### Step 6 - Reconcile the Cost Lanes

Produce a cost-lane table:

| Lane | Required treatment |
| --- | --- |
| Approved budget | State source, date, GST basis and whether reviewed or draft |
| Forecast final cost | Reconcile to current cost plan or QS report; explain if PM fee, GST or escalation sit outside line-item totals |
| Committed | Include only accepted appointments, contracts, POs and approved variations |
| Paid | Include only paid invoices/claims; derive ex GST from inc GST only when stated and label the derivation |
| Pending | Include unaccepted proposals, pending variations, pending claims and scope choices with decision owner |
| Contingency | Separate design, construction and special allowances; show drawdown, remaining and evidence |
| Variance | Explain budget variance and likely pressure using source-backed arithmetic |

Minimum checks:

- GST basis is explicit for every total.
- Owner budget aspiration is not treated as approved project budget unless a decision record says so.
- QS all-up budget-setting figure is not silently forced to reconcile with a line-item table that excludes GST, PM fee or escalation.
- Paid amounts are not created from unpaid invoices or issued proposals.
- Pending consultant proposals are not commitments.
- Pending variations do not reduce contingency unless approved drawdown evidence exists.
- Contingency is not used to hide base-scope budget pressure.

### Step 7 - Explain Contingency

Report contingency as a control, not a spare budget bucket.

Separate:

- design development contingency;
- construction contingency;
- special risk allowances, e.g. neighbour/APZ, latent conditions, percolation testing;
- approved drawdowns;
- pending or proposed drawdowns;
- remaining unallocated contingency;
- contingency risks.

If no contingency register exists, report the cost-plan contingency line as an allowance only and draft a register-opening action. Do not say contingency is available or spent without evidence.

### Step 8 - Detect Budget Pressure Early

Escalate early when any of these appear:

- forecast final cost exceeds approved budget or owner funding limit;
- pending variations or scope decisions are likely to consume contingency;
- contingency has no register or approved drawdown trail;
- owner aspiration conflicts with QS, tender, contract or cost-plan evidence;
- consultant, authority, compliance, design or programme gaps are likely to move cost;
- invoices, claims or variations are being carried without allocation to cost items;
- cost plan is stale after design, authority, procurement or programme movement;
- scope has increased without an owner decision or approved budget update;
- formal QS input is required but not engaged or current.

Route material pressure to `escalation-note-system.md`. Route owner decisions to `decision-record-system.md`. Route stale controls to `register-maintenance-system.md` or `cost-plan-system.md`.

### Step 9 - Draft the Report

Every output is a draft for review.

Minimum frontmatter:

```yaml
---
status: draft
author: agent
date: YYYY-MM-DD
reporting_period: YYYY-MM
audience: owner | internal | contractual | mixed
gst_basis: ex-GST | inc-GST | mixed | unknown
seed_consulted: []
evidence_refs: []
source_controls: []
control_gaps: []
---
```

Minimum body:

1. Cost status in one sentence.
2. Cost pressure and decisions needed.
3. Source-control reconciliation.
4. Cost-lane table: approved budget, forecast, committed, paid, pending, contingency, variance.
5. Contingency movement and remaining position.
6. Invoice/claim/variation reconciliation.
7. Budget pressure and escalation triggers.
8. Handoffs and next actions.
9. Assumptions, gaps and cost evidence conflicts.

For owner-facing updates, use stakeholder voice and lead with what the cost position means and what decision is needed. Keep dense reconciliation in background detail.

### Step 10 - Route Handoffs

Create follow-up actions, not silent assumptions:

- Baseline or stale cost plan -> `cost-plan-system.md`.
- Detailed project report summary -> `project-report-system.md`.
- Progress claim assessment -> `progress-claim-assessment-system.md`.
- Variation or EOT cost impact -> `variation-management-system.md`.
- Budget pressure -> `escalation-note-system.md`.
- Owner budget/scope decision -> `decision-record-system.md`.
- Missing/stale register -> `register-maintenance-system.md`.
- Programme cost impact -> `programme-system.md`.
- Authority-driven cost movement -> `authority-approvals-system.md`.
- Consultant fee/scope ambiguity -> `consultant-coordination-system.md`.
- Design cost movement -> `design-review-evaluation-system.md`.

### Step 11 - Quality Check

Before returning, check:

- every headline figure has a source and GST basis;
- every cost line has one clear status;
- consultant invoices, contractor claims and internal forecasts are separated;
- contingency drawdown is explained and not used as scope money;
- budget pressure is visible near the top;
- cost evidence conflicts are visible;
- missing cost controls are named as gaps;
- no Excel register/workbook has been changed without Excel-safe skills.

## Guardrails

- Do not bypass the three-overlay declaration gate.
- Do not use another project's evidence.
- Do not mix consultant invoices, contractor claims and internal forecasts without status.
- Do not treat issued proposals as committed costs.
- Do not treat claimed or invoiced amounts as paid without payment evidence.
- Do not hide budget pressure until a milestone.
- Do not use contingency as scope money.
- Do not use the NSW residential cost reference as active-project evidence or rate advice.
- Do not overwrite Excel registers or workbooks without Excel-safe skills.
- Do not write to `project.db`.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/evidence-sweep.md` - active-project evidence sweep.
- `../atomic/seed-targeted-read.md` - targeted cost seed loading.
- `../atomic/markdown-draft-for-review.md` - draft markdown output discipline.
- `../atomic/register-row-draft.md` - cost, invoice, variation, contingency, action and decision row drafting.
- `../atomic/excel-safe-edit.md` - controlled workbook edits.
- `../atomic/excel-verify.md` - workbook verification.
- `../reference/nsw-residential-cost-breakdown-reference.md` - NSW residential cost taxonomy reference.
- `cost-plan-system.md` - baseline and updated cost plan workflow.
- `project-report-system.md` - integrated time/cost/scope/quality/risk reporting.
- `progress-claim-assessment-system.md` - payment claim assessment.
- `variation-management-system.md` - variation and EOT cost impact assessment.
- `decision-record-system.md` - owner/project-lead cost decisions.
- `escalation-note-system.md` - budget-pressure early warnings.
- `register-maintenance-system.md` - stale or missing register controls.
- `../../00-doctrine/doctrine.md` - cost, evidence, register, decision, voice and escalation discipline.

## Fixture Check

Use `../../99-docs/issues/sitewise-skills-framework-alignment/fixtures/cost-report/bennett-cost-report-fixture-check.md` as the regression fixture. A passing review produces:

- a cost-source reconciliation that keeps QS forecast, draft cost-plan totals, owner budget aspiration, builder ballpark and paid consultant invoice evidence separate;
- a cost-lane table with approved budget, forecast, committed, paid, pending and contingency statuses;
- early budget-pressure escalation for the Bennett affordability gap;
- control gaps for absent invoice, variation and contingency registers rather than invented certainty.
