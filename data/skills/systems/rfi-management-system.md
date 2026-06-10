# System skill: rfi-management-system

**Job:** Manage SiteWise RFI intake, routing, response coordination and register control so project questions are logged, answered in writing, tracked to due dates, and escalated when they threaten cost, programme, scope, quality or authority controls.

This system inherits `../_shared/pm-contract.md`. It is the canonical SiteWise workflow for the framework alias `rfi-management`.

## When to Use

Use this skill when:

- the user asks to log, issue, route, answer, close, audit or report an RFI;
- a design, consultant, builder, subcontractor, supplier, certifier or authority question needs a documented response path;
- a verbal answer, meeting discussion or email thread needs to become a controlled RFI or confirmation record;
- a drawing, specification, scope, consultant advice, authority condition, tender addendum, site issue or construction detail is unclear;
- stale RFIs, overdue responses, missing owners, unclear due dates or undocumented answers need register control;
- an RFI may affect cost, programme, variation, EOT, procurement, claim, authority, design responsibility, construction release, PC, OC or handover.

This skill coordinates questions and responses. It does not issue directions outside the project lead's authority, approve changes, certify compliance, assess entitlement, or replace the responsible designer, consultant, certifier, builder or contract administrator.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Mode** - `log-rfi`, `issue-rfi`, `route-rfi`, `draft-response`, `response-review`, `close-rfi`, `stale-rfi-review`, `rfi-register-audit`, or `rfi-impact-check`. Defaults to `log-rfi` for a new question and `stale-rfi-review` where a register exists.
- **RFI source** - required for a real RFI: email, minute, site note, drawing, claim, tender query, consultant advice, photo, defect, authority condition or verbal-answer confirmation note.
- **Question / issue** - required.
- **Requested recipient** - optional; if absent, determine from responsibility evidence and flag uncertainty.
- **Due date** - optional; if absent, derive from contract, tender, programme or review cadence where evidenced, otherwise flag gap.
- **Affected documents or scope** - optional.
- **Known cost/programme/authority impact** - optional.
- **Output path override** - optional.

The skill reads project evidence only from the active project folder.

## Output Location

| Output | Default path |
| --- | --- |
| Formal construction RFI register | `07-construction/08-rfi-notices/rfi-register.md` |
| Formal construction RFI draft | `07-construction/08-rfi-notices/RFI-<seq>-<short-topic>.md` |
| Design RFI register | `03-design/design-rfi-register.md` or `07-construction/08-rfi-notices/design-rfi-register.md` |
| Design RFI draft | `03-design/design-rfis/DRFI-<seq>-<short-topic>.md` or `07-construction/08-rfi-notices/DRFI-<seq>-<short-topic>.md` |
| Consultant clarification register | `02-consultant/consultant-rfi-register.md` |
| Tender clarification / addenda log | `05-procurement/tender-rfi-addenda-register.md` where procurement evidence controls the question |
| RFI stale report | `07-construction/08-rfi-notices/rfi-stale-report-YYYY-MM-DD.md` |
| Owner-facing RFI impact summary | `08-meetings-reporting/owner-rfi-impact-summary-YYYY-MM-DD.md` |

All markdown outputs go through `../atomic/markdown-draft-for-review.md`. RFI, design RFI, action, risk, decision, variation, EOT and notice rows go through `../atomic/register-row-draft.md`. Excel edits go through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` only after a reviewed update plan.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before RFI work:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration.
4. Confirm the RFI lane: design, consultant, tender/procurement, construction, authority, handover or mixed.
5. Do not read another project folder, draft RFI outputs, or create register rows until the gate passes.

## Sequence

### Step 1 - Seed Stance

RFI logging is normally evidence/register-led and does not require routine seed loading. Record `seed_consulted: []` when the task only logs, routes or tracks a question.

Invoke `../atomic/seed-targeted-read.md` only when the RFI requires a role-shaped judgement, technical interpretation, contract/authority context, or escalation recommendation. Load only the relevant seeds:

- Tier 2 archetype seed per `archetype:`;
- Tier 3 role overlay per `user_role:`;
- `../../01-seed/contract-administration-guide.md` where the RFI affects directions, notices, claims, variations, EOTs, PC, OC or contract administration;
- `../../01-seed/program-scheduling-guide.md` where the RFI affects milestone, critical path, lead time or delay exposure;
- `../../01-seed/cost-management-principles.md` where the RFI affects budget, claim, variation, contingency or cost plan;
- `../../01-seed/procurement-quoting-guide.md` where the question is a tender clarification or addendum;
- `../../01-seed/sustainability-energy-guide.md`, `../../01-seed/ncc-reference-guide.md` or trade seeds where technical literacy is needed to frame the question or route it.

Do not answer technical design or certification questions from seed knowledge. Use seeds to ask better questions and identify responsibility, not to replace the responsible professional.

### Step 2 - Evidence Sweep

Invoke `../atomic/evidence-sweep.md` with task subject `RFI: <mode> <short topic>`.

High-relevance evidence:

- `README.md` for project boundary, phase and overlays;
- `00-brief-pmp/` for role, contract setup, decision rights, PMP communication rules and owner decisions;
- `01-cost/` for cost plan, cost reports, claims, variations and budget implications;
- `02-consultant/` for consultant appointment scope, responsibility matrix, advice register and deliverables;
- `03-design/` for drawings, specifications, design reviews, design deliverables and design RFIs;
- `04-planning-and-authorities/` for approvals, consent conditions, certifier advice and authority requirements;
- `05-procurement/` for tender questions, addenda, clarifications, returnables and recommendation evidence;
- `06-programme/` for baseline dates, milestones, lookaheads, critical path and delay register;
- `07-construction/08-rfi-notices/` for existing RFIs, notices, responses and formal records;
- `07-construction/` generally for site reports, photos, inspections, defects, claims, variations and EOTs;
- `08-meetings-reporting/` for minutes, action register, decision register, owner updates and escalation notes;
- `09-handover-dlp/` for PC, OC, defects, warranties, manuals and DLP questions.

If the source is verbal, record the verbal source as incomplete and create a confirmation path. Do not treat it as a documented answer.

### Step 3 - Classify the RFI Lane

Classify each question before logging:

| Lane | Use when | Typical register |
| --- | --- | --- |
| `design-rfi` | Drawing/specification/design responsibility question before or during construction | Design RFI register |
| `consultant-clarification` | Consultant advice, deliverable, scope or responsibility is unclear | Consultant RFI/action/advice register |
| `construction-rfi` | Builder/subcontractor/site question affects construction work, scope, quality or sequencing | RFI register in `07-construction/08-rfi-notices/` |
| `tender-clarification` | Tenderer asks a question before award | Tender RFI/addenda register, with `procurement-evaluation-system.md` handoff |
| `authority-rfi` | Authority, certifier or approval condition needs clarification | Authority tracker plus RFI/action row |
| `handover-rfi` | PC, OC, manuals, warranties, defects or DLP question | Handover tracker plus RFI/action row |

If the question is actually a variation request, delay notice, payment claim dispute, defect, design decision, authority condition or owner decision, log the RFI only if a question still needs a response, then route the substantive matter to the correct system.

### Step 4 - Resolve Authority and Responsibility

Before drafting a response or issuing a request, identify:

- who asked the question;
- who owns the response;
- who is authorised to answer;
- whether the answer may become a direction;
- whether the project lead is appointed to issue or coordinate that direction;
- whether owner, Principal, Superintendent, certifier, designer, engineer, builder or consultant approval is required.

Use active-project appointment evidence first. If authority is unclear, draft an authority/role gap instead of issuing the RFI or response.

Do not direct works outside contractual authority. Do not tell a builder or subcontractor to proceed, change scope, accelerate, omit work, accept a substitute, or vary a specification unless the active project evidence shows the project lead has that authority and the required formal mechanism is followed.

### Step 5 - Draft or Update the Register Row

Use `../atomic/register-row-draft.md`.

Use register type:

- `RFI register` for formal construction RFIs;
- `Design RFI register` for design/document questions;
- `Action register` where the item is an internal clarification action rather than a formal RFI;
- `Consultant advice register` where a response has been received and affects project controls;
- `Contractual notices register` where the RFI has notice implications.

Minimum RFI row fields:

| Field | Required treatment |
| --- | --- |
| `ID` | `RFI-<seq>` or `DRFI-<seq>`; use `<TBD>` only for draft row before register insertion |
| `Description` | The question in one to three plain sentences |
| `Owner` | One response owner, not "project" or "TBC" |
| `Status` | `issued`, `awaiting-response`, `responded`, `closed` or `superseded` |
| `Due date` | Response due date or next-action deadline |
| `Source` | Evidence path, email/minute/site record/photo, or verbal confirmation gap |
| `Next action` | Specific next action by owner |
| `Date issued` | Date the RFI was or will be issued |
| `Recipient` | Party responsible for answering |
| `Date response due` | Same as due date unless existing register separates these |
| `Date responded` | Blank until written response received |
| `Response summary` | Blank until written response received; never "verbal only" as final answer |

If any mandatory row field is missing, return a gap report and draft what needs to be confirmed before the row is committed.

### Step 6 - Draft the RFI or Response Path

For a new RFI, draft:

1. RFI number or draft placeholder.
2. Source and evidence basis.
3. Question.
4. Affected drawings/specifications/conditions/works.
5. Required response format.
6. Required response date.
7. Impact if unresolved.
8. Routing and recipient.
9. Statement that the RFI is not a direction or approval unless separately authorised.

For a response, draft:

1. Response source and respondent.
2. Response date.
3. Answer summary.
4. Whether the response fully answers the question.
5. Cost, programme, scope, quality, authority and safety implications.
6. Whether a decision, variation, EOT, notice, design update, approval update, claim assessment or construction release action is needed.
7. Whether the RFI can close.

Do not close an RFI on a verbal answer. If a verbal answer is useful, draft a confirmation request and keep the RFI `awaiting-response` until the written response is received.

### Step 7 - Check Cost, Programme and Authority Impact

Classify impact:

| Impact | Route |
| --- | --- |
| Cost or scope change | `variation-management-system.md`, `cost-report-system.md`, `decision-record-system.md` where owner sign-off is needed |
| Programme or critical-path risk | `programme-system.md`, `escalation-note-system.md` where timing is threatened |
| Payment claim effect | `progress-claim-assessment-system.md` |
| Authority or compliance effect | `authority-approvals-system.md` |
| Consultant responsibility or advice effect | `consultant-coordination-system.md` |
| Design maturity or drawing status effect | `design-review-evaluation-system.md` |
| Risk remains open | `risk-register-system.md` |
| Register stale or incomplete | `register-maintenance-system.md` |

If critical path or budget is threatened, surface the escalation trigger. Do not wait for the next monthly report.

### Step 8 - Track Stale RFIs

For stale review:

1. Find all open/awaiting-response RFI rows.
2. Compare response due dates to today's date.
3. Identify RFIs with missing owner, missing due date, missing source, no affected document, no impact classification or verbal-only answer.
4. Sort by critical path, authority, cost and construction-release impact.
5. Draft follow-up rows or reminder notices.
6. Escalate overdue critical RFIs through `escalation-note-system.md`.

Stale RFIs must not sit only in an internal note. They need an owner, due date and next action.

### Step 9 - Role and Archetype Shaping

Apply role overlay:

- Owner-builder: keep the trail simple and self-protective; do not let trade verbal answers replace records.
- Architect-PM: separate architect/design advice from PM coordination and owner decision advice; use owner-facing summaries where RFIs require owner decision.
- Builder: keep RFIs inside contractual authority and route design/engineer/certifier questions to the responsible party.
- D&C: maintain design responsibility, consultant response, certifier submission and construction-release links; design RFIs cannot drift by silence.

Apply archetype risks:

- New dwelling: structure, siteworks, bushfire, wastewater, BASIX/NatHERS, authority, glazing, pool, services and inspection RFIs commonly affect cost/programme.
- Renovation: latent conditions, existing structure, waterproofing tie-ins, services, hazardous materials and live-occupancy RFIs commonly affect variations.
- Multi-dwelling: fire/acoustic/access, party walls, metering, strata/subdivision and staged OC RFIs need stronger register control.
- Ancillary/small-commercial: classification, fire/access, planning and service interface RFIs may need certifier or authority advice.

### Step 10 - Draft the Output

Every output is a draft for review.

Minimum frontmatter:

```yaml
---
status: draft
author: agent
date: YYYY-MM-DD
rfi_id: RFI-<seq> | DRFI-<seq> | draft
mode: log-rfi | issue-rfi | draft-response | stale-rfi-review
seed_consulted: []
evidence_refs: []
---
```

Minimum body for an RFI draft:

1. RFI status and limits.
2. Source/evidence basis.
3. Question.
4. Recipient and response owner.
5. Affected documents/works.
6. Due date.
7. Impact if unresolved.
8. Register row draft.
9. Handoffs.
10. Assumptions and gaps.

Minimum body for a stale review:

1. Register reviewed.
2. Stale/overdue RFI table.
3. Critical impacts.
4. Follow-up actions.
5. Escalations.
6. Register hygiene gaps.

### Step 11 - Return Summary

Return:

- RFI draft path or register row drafted;
- recipient and response owner;
- status and due date;
- cost/programme/authority impact;
- handoffs created;
- gaps or verbal-answer confirmations needed;
- tests or fixture checks run.

## Guardrails

- Do not bypass the three-overlay declaration gate.
- Do not use another project's evidence.
- Do not direct works outside contractual authority.
- Do not let a verbal answer replace a documented response.
- Do not close an RFI without a written response or superseding record.
- Do not use an RFI to approve a variation, EOT, claim, substitution, design change or authority pathway.
- Do not leave an RFI without one owner and one due date.
- Do not bury critical-path or budget threats inside the RFI register.
- Do not update Excel registers without Excel-safe skills.
- Do not write to `project.db`.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/evidence-sweep.md` - active-project evidence sweep.
- `../atomic/register-row-draft.md` - RFI and design RFI row drafting.
- `../atomic/markdown-draft-for-review.md` - draft RFI and response outputs.
- `consultant-coordination-system.md` - consultant scope, advice and deliverable routing.
- `design-review-evaluation-system.md` - design status and design-risk questions.
- `authority-approvals-system.md` - approval and certifier questions.
- `programme-system.md` - programme impact and stale critical-path RFIs.
- `cost-report-system.md` - cost impact and budget pressure.
- `variation-management-system.md` - variation/EOT consequences and written direction discipline.
- `progress-claim-assessment-system.md` - payment claim impact.
- `decision-record-system.md` - owner/project-lead decisions.
- `escalation-note-system.md` - critical-path, budget, authority or role escalation.
- `register-maintenance-system.md` - stale register and hygiene checks.
- `../../00-doctrine/doctrine.md` - evidence, register, voice, decision and escalation discipline.

## Fixture Check

Use `../../99-docs/issues/sitewise-skills-framework-alignment/fixtures/rfi-management/bennett-rfi-management-fixture-check.md` as the regression fixture. A passing review produces:

- draft design RFI/register rows for missing current Rev B elevations/sections and BAL-FZ/BASIX coordination;
- response paths to the responsible architect/consultants rather than an agent answer;
- stale/impact routing for authority, programme and budget threats;
- explicit refusal to treat verbal answers or superseded drawings as final responses.
