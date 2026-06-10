# System skill: register-maintenance-system

**Job:** Audit, reconcile, and maintain SiteWise project registers so every row remains current, sourced, owned, date-bound, and useful for decision and claim reconstruction.

This system inherits `../_shared/pm-contract.md`. It generalises the `quality-check` pattern in `risk-register-system.md` across action, decision, cost, programme, risk, RFI, variation, defects, authority, conditions, consultant, design, subcontractor, owner-supplied-item, inspection, EOT and handover registers.

## When to Use

Use this skill when:

- the user asks to create, update, reconcile, clean up, or audit a register;
- a workflow discovers stale, owner-less, status-less, unsourced, or overdue rows;
- a report or phase-gate deliverable needs a trustworthy current register before drafting;
- an Excel register needs a controlled update path;
- Markdown register rows need a hygiene report before being accepted as live project controls.

This is a continuous Tier 1 evidence-control workflow. It is not itself a cost, programme, procurement, variation, claim, risk, or handover assessment; it keeps the register substrate trustworthy for those systems.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Mode** - `audit-register`, `reconcile-register`, `open-register`, `update-register`, or `stale-row-report`. Required unless the request makes it obvious.
- **Register type** - required unless auditing all registers.
- **Register path** - optional; if omitted, the skill discovers candidate registers in the active project.
- **Cut-off date** - optional; defaults to today's ISO date for overdue/stale checks.
- **Destination format** - `markdown`, `excel`, or `report-only`. Defaults to the existing register substrate.
- **Scope focus** - optional, e.g. `overdue RFIs`, `variation register`, `owner-builder park-for-decision queue`, `D&C design deliverables`.

The skill reads project evidence only from the active project folder.

## Output Location

- Hygiene report: same folder as the audited register, named `<register-name>-hygiene-report-vNN.md`.
- Markdown register draft updates: existing register folder, as a review draft or proposed replacement table.
- Excel register updates: same workbook path, only through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md`.
- Register opening drafts: standard register folders from `contract-setup-system.md` and `setup-and-commission-guide.md`.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before auditing or drafting:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration.
4. Do not run evidence-sweep, inspect rows, draft updates, or write hygiene reports until the gate passes.

## Sequence

### Step 1 - Evidence Sweep

Invoke `../atomic/evidence-sweep.md` with task subject `register maintenance: <register type or scope focus>`.

Discover register candidates in:

- `00-brief-pmp/` - risk, owner-supplied items, brief decisions;
- `01-cost/` - cost register, cost plan, invoice trackers, contingency and variation cost links;
- `02-consultant/` - consultant advice and design responsibility registers;
- `03-design/` - drawing, design deliverables, design RFI and design decision registers;
- `04-planning-and-authorities/` - authority approvals and consent conditions;
- `05-procurement/` - tender, subcontractor, clarification and award registers;
- `06-programme/` - master programme, milestone tracker, lookahead and delay register;
- `07-construction/` - progress claim, variation, EOT, RFI, notice, defects, inspection and site report registers;
- `08-meetings-reporting/` - action, decision, risk and meeting registers;
- `09-handover-dlp/` - handover, defects, warranties, O&M and DLP close-out registers.

If no register exists for a requested type, return an open-register path and draft the header plus opening row. Do not pretend an absent register is current.

### Step 2 - Identify Register Type and Substrate

Classify the target register:

| Substrate | Behaviour |
| --- | --- |
| Markdown table | Parse the header and rows, audit each row, and draft a hygiene report. Proposed row fixes are review drafts. |
| Excel workbook | Inspect workbook structure and headers; route all writes through `excel-safe-edit` and verification through `excel-verify`. |
| Narrative markdown | Flag as not a structured register if row fields cannot be parsed. Draft a migration recommendation. |
| Missing register | Draft an open-register action and starter table. |

Use existing project register schema where established. Where schema is absent, apply the seven-field doctrine schema.

### Step 3 - Check the Seven Mandatory Fields

Every register row must contain:

1. ID.
2. Description.
3. Owner.
4. Status.
5. Due date or review date.
6. Source / evidence reference.
7. Next action.

Flag:

- missing IDs;
- duplicate IDs;
- blank descriptions;
- owner values such as `Project`, `TBC`, `Unknown`, or committee names without an accountable party;
- missing or invalid status;
- missing, non-ISO, impossible, or stale due/review dates;
- missing source / evidence references;
- vague next actions such as `monitor`, `follow up`, `review`, `TBC`, or `as required`;
- rows whose next action contradicts status, e.g. `closed` with unresolved action.

### Step 4 - Check Type-Specific Discipline

Use the register type to check extra required fields:

| Register type | Additional hygiene checks |
| --- | --- |
| Decision | Append-only state, `Supersedes` / `Superseded-by` links, decision-maker, basis, consequences. |
| Action | Owner, due date, originating forum, overdue status. |
| Risk | Likelihood, consequence, mitigation, residual rating, review date, escalation for high residual risk. |
| Cost | Cost item, approved/forecast/committed/paid/pending separation, source totals. |
| Programme | Milestone, baseline date, current forecast, movement reason, critical-path flag. |
| Variation | Direction, price, time impact, owner/Principal sign-off, status and cost-plan link. |
| EOT | Notice date, cause, days claimed/granted, programme evidence and assessment status. |
| RFI / notice | Recipient, date issued, response due date, response status, clause/discipline where relevant. |
| Defects | Location, trade, severity, notified date, due date, closure evidence. |
| Authority / conditions | Authority, condition number, required-by stage, evidence status, delivery owner. |
| Consultant / design | Discipline, appointment/scope basis, deliverable reference, revision and reviewer status. |

Where the existing register does not support a type-specific column, flag the gap as a schema improvement rather than inventing a silent value.

### Step 5 - Reconcile Rows to Evidence

For each open row, check whether the source reference points to an active-project artefact or clear source identifier.

Return one of:

- `verified` - source evidence exists and supports the row;
- `source-missing` - the reference is blank or not found;
- `source-conflict` - evidence conflicts with the row;
- `stale-evidence` - row relies on superseded or older evidence;
- `not-checked` - source is a conversation/email identifier not available in project files.

Do not read another project folder to resolve a missing source.

### Step 6 - Produce the Hygiene Report

Use `../atomic/markdown-draft-for-review.md` to draft the hygiene report.

Minimum sections:

- register audited;
- register type and substrate;
- date of audit;
- rows checked;
- critical defects;
- overdue or stale rows;
- missing mandatory fields;
- source/evidence gaps;
- duplicate or invalid IDs;
- schema improvement recommendations;
- proposed next actions.

The report is a draft for review. It does not silently update the live register.

### Step 7 - Draft Row Fixes or Updates

For new or corrected rows, call `../atomic/register-row-draft.md` one row at a time.

For Markdown registers:

- return proposed rows or a proposed replacement table as a draft;
- do not overwrite a reviewed register unless the user expressly approves the update path;
- preserve historical rows and supersession links.

For Excel registers:

1. Prepare the approved update plan.
2. Use `../atomic/excel-safe-edit.md` for the controlled edit.
3. Use `../atomic/excel-verify.md` before reporting completion.
4. If verification fails, report the workbook as not current.

### Step 8 - Surface Escalations

Surface, at minimum:

- overdue owner/Principal/self decisions;
- high risk without escalation;
- stale critical-path, authority, RFI, EOT, variation, claim, defect, insurance or approval rows;
- rows where missing source evidence prevents payment, award, variation, EOT, handover or compliance reliance;
- repeated owner-less rows in a live control register;
- Excel verification failures.

Escalation routing follows the role overlay and `../../00-doctrine/doctrine.md` escalation triggers. Route each escalation through `escalation-note-system.md` and report the trigger, route and recommended action in the return summary.

### Step 9 - Return Summary

Return:

- mode used;
- register path(s);
- substrate;
- rows checked;
- row defects by severity;
- stale/overdue rows;
- source conflicts;
- row fixes drafted;
- Excel edit/verify status where applicable;
- open escalations;
- recommended next action.

## Rules / Must Not Do

- Do not close a row without evidence.
- Do not hide narrative commentary inside register cells.
- Do not silently replace a live register.
- Do not rewrite source evidence.
- Do not treat a register as current where required fields are missing.
- Do not read another project folder to repair a source gap.
- Do not write `project.db`.
- Do not edit Excel without `excel-safe-edit` and `excel-verify`.

## Fixture Checks

Use `../../99-docs/issues/sitewise-skills-framework-alignment/fixtures/register-maintenance/markdown-register-fixture.md` for a Markdown audit dry-run.

Expected defects:

- one valid action row passes the seven-field check;
- one row is missing owner, source and specific next action;
- one row has a duplicate ID and overdue due date;
- hygiene report recommends source repair, owner assignment, ID correction and due-date escalation.

The check is report-only and does not write a live project register.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/evidence-sweep.md` - active-project evidence discovery.
- `../atomic/register-row-draft.md` - one-row drafting discipline.
- `../atomic/markdown-draft-for-review.md` - hygiene report draft wrapper.
- `../atomic/excel-safe-edit.md` - controlled Excel edit path.
- `../atomic/excel-verify.md` - post-edit Excel verification.
- `risk-register-system.md` - source of the risk `quality-check` pattern.
- `../../00-doctrine/doctrine.md` register discipline, evidence discipline and escalation triggers.
