# System skill: meeting-minutes-system

**Job:** Produce SiteWise meeting records that separate discussion, confirmed decisions, open decisions and actions, then route register rows and escalations so meetings become controlled project evidence rather than loose conversation.

This system inherits `../_shared/pm-contract.md`. It is the canonical SiteWise workflow for the framework alias `meeting-minutes`.

## When to Use

Use this skill when:

- the user asks to draft meeting minutes, site minutes, owner meeting notes, consultant coordination minutes, tender meeting notes, design review minutes or action minutes;
- raw meeting notes, transcript, email recap or agenda need to become a controlled meeting record;
- decisions made in a meeting need to be separated from discussion and routed to `decision-record-system.md`;
- actions need owner, due date, status, source and next action;
- a meeting surfaces an escalation trigger, RFI, variation, EOT, cost issue, programme issue, authority issue, consultant gap, design question or handover blocker;
- previous minutes, actions or decisions need stale-action review before the next meeting.

This skill records and coordinates meeting outcomes. It does not create a decision where none was made, issue contractual directions, approve variations, certify progress, close risks, or replace the responsible decision-maker.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Meeting source** - required: notes, transcript, agenda, email recap, Teams summary, site report, consultant coordination note or handwritten notes.
- **Mode** - `draft-minutes`, `action-minutes`, `site-minutes`, `owner-meeting-minutes`, `consultant-coordination-minutes`, `design-review-minutes`, `tender-meeting-minutes`, `minutes-quality-check`, or `stale-action-review`. Defaults to `draft-minutes`.
- **Meeting date** - required unless clear from source.
- **Meeting forum / purpose** - required unless clear from source.
- **Attendees and apologies** - optional; if absent, flag gap.
- **Previous minutes/action register path** - optional.
- **Decision register path** - optional.
- **Output path override** - optional.

The skill reads project evidence only from the active project folder.

## Output Location

| Output | Default path |
| --- | --- |
| Owner meeting minutes | `08-meetings-reporting/owner-meeting-minutes-YYYY-MM-DD.md` |
| Internal project minutes | `08-meetings-reporting/project-meeting-minutes-YYYY-MM-DD.md` |
| Consultant coordination minutes | `02-consultant/consultant-coordination-minutes-YYYY-MM-DD.md` or `08-meetings-reporting/consultant-coordination-minutes-YYYY-MM-DD.md` |
| Design review minutes | `03-design/design-review-minutes-YYYY-MM-DD.md` |
| Site meeting minutes | `07-construction/12-reports/site-meeting-minutes-YYYY-MM-DD.md` |
| Tender meeting minutes | `05-procurement/tender-meeting-minutes-YYYY-MM-DD.md` |
| Action minutes / stale action review | `08-meetings-reporting/action-minutes-YYYY-MM-DD.md` |
| Owner-facing decision summary | `08-meetings-reporting/owner-decision-summary-YYYY-MM-DD.md` |

All markdown outputs go through `../atomic/markdown-draft-for-review.md`. Action, decision, risk, RFI, variation, EOT, authority and escalation rows go through `../atomic/register-row-draft.md`. Excel register edits go through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` only after a reviewed update plan.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before meeting-minutes work:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration.
4. Confirm the meeting source, meeting date, forum, audience and intended output.
5. Do not read another project folder, draft minutes, or create register rows until the gate passes.

## Sequence

### Step 1 - Classify Meeting Type and Voice

Classify the meeting before drafting:

| Meeting type | Default voice | Primary controls |
| --- | --- | --- |
| Owner meeting | Stakeholder register | Owner decisions, action register, escalation notes |
| Internal PM meeting | Contractual register | Actions, risks, programme/cost/status controls |
| Consultant coordination | Contractual register | Consultant advice, RFIs, deliverables, authority/design handoffs |
| Design review | Contractual register | Design decisions, design RFIs, design-risk view |
| Tender meeting | Contractual register | Tender RFIs/addenda, probity, procurement actions |
| Site meeting | Contractual register | RFIs, variations, EOTs, inspections, defects, progress claims |
| Handover meeting | Contractual or stakeholder per audience | Defects, PC/OC, warranties, manuals, DLP actions |

If the meeting has mixed audiences, split owner-facing explanation from formal record sections. Do not collapse contractual language and owner guidance where the audiences differ.

### Step 2 - Seed Stance

Meeting minutes are normally evidence/register-led and do not require routine topic seeds. Record `seed_consulted: []` when the skill only records a meeting and drafts register rows.

Invoke `../atomic/seed-targeted-read.md` only when the minutes contain a new role-shaped recommendation, technical interpretation, authority judgement, contract implication or escalation. Load only relevant seeds:

- Tier 2 archetype seed per `archetype:`;
- Tier 3 role overlay per `user_role:`;
- `../../01-seed/contract-administration-guide.md` where directions, variations, EOTs, claims, RFIs, PC, OC or notices are discussed;
- `../../01-seed/cost-management-principles.md` where budget, contingency, claim, invoice or variation matters are discussed;
- `../../01-seed/program-scheduling-guide.md` where milestones, critical path, lookahead or delay exposure is discussed;
- `../../01-seed/procurement-quoting-guide.md` where tender, addenda or procurement recommendations are discussed;
- `../../01-seed/sustainability-energy-guide.md`, `../../01-seed/ncc-reference-guide.md` or trade seeds where technical/authority literacy is needed.

Use seeds to shape routing and escalation. Do not turn seed guidance into a meeting decision without meeting evidence.

### Step 3 - Evidence Sweep

Invoke `../atomic/evidence-sweep.md` with task subject `meeting minutes: <mode> <meeting date> <forum>`.

High-relevance evidence:

- the meeting source itself;
- `README.md` for project boundary, phase and overlays;
- `00-brief-pmp/` for PMP, role, decision rights, owner brief and setup gaps;
- `01-cost/` for cost plans, cost reports, claims, variations and budget decisions;
- `02-consultant/` for consultant appointment, advice, deliverables and responsibility;
- `03-design/` for design status, drawing revisions, design RFIs and design decisions;
- `04-planning-and-authorities/` for authority pathway, approvals, conditions and certifier advice;
- `05-procurement/` for tender, RFIs, addenda, evaluation and award actions;
- `06-programme/` for baseline dates, milestones, lookaheads and delay records;
- `07-construction/` for RFIs, notices, claims, variations, site reports, photos, inspections and defects;
- `08-meetings-reporting/` for previous minutes, action register, decision register, risk register and owner updates;
- `09-handover-dlp/` for PC, OC, handover, defects, warranties and DLP actions.

If the meeting source is missing or only described verbally, draft a meeting-record gap and ask for source notes before producing sign-off-ready minutes.

### Step 4 - Establish Meeting Control Data

Every minutes output must state:

- project;
- meeting title/forum;
- date;
- time if known;
- location or medium;
- chair/facilitator if known;
- minute taker if known;
- attendees;
- apologies;
- source notes/transcript/email reference;
- issue status: draft, reviewed or superseded;
- previous minutes/action register reviewed, if applicable.

If attendees, date, source or meeting purpose are missing, flag them as gaps. Do not invent them.

### Step 5 - Separate Discussion, Decisions, Actions and Open Questions

Classify every useful meeting item:

| Category | Test |
| --- | --- |
| Discussion | Context, options, concerns, background or commentary. It is not binding by itself. |
| Confirmed decision | The decision-maker/forum clearly decided something, with enough evidence to record the decision. |
| Open decision | A choice is needed, but no decision was made. Route to decision request or park-for-decision queue. |
| Action | Someone must do something by a due date. It needs owner, status, due date, source and next action. |
| RFI / clarification | A question needs a documented response. Route to `rfi-management-system.md`. |
| Escalation | Budget, programme, authority, scope, safety, compliance, role or evidence trigger needs recommended action. Route to `escalation-note-system.md`. |

Discussion is never recorded in place of a decision. If the source says only "discussed", "noted", "considered" or "agreed to investigate", record discussion or action, not a decision.

### Step 6 - Draft Decision Rows

Route confirmed decisions to `decision-record-system.md`.

A decision must include:

- decision text;
- decision-maker or forum;
- decision date;
- source quote or source reference;
- basis;
- alternatives where material;
- consequences for cost, time, scope, quality and risk;
- follow-up actions;
- supersedes/superseded-by if applicable.

If the source is an owner or Principal direction, quote the source wording where available. Do not paraphrase the direction into a softer or broader decision.

If a decision is not confirmed, draft an open-decision prompt instead of a decision row.

### Step 7 - Draft Action Rows

Use `../atomic/register-row-draft.md` as register type `Action register`.

Every action row must have:

- ID: `A-<seq>` or `A-<TBD>` for draft;
- description;
- one owner;
- status: `open`, `in-progress`, `closed` or `cancelled`;
- due date in ISO format;
- source/evidence reference;
- next action;
- date raised;
- originating forum;
- date closed if closed.

No vague action rows. "Team to consider", "project to follow up" and "TBC" are gaps, not actions.

### Step 8 - Maintain Prior Actions

If previous minutes or an action register exists:

1. List prior open actions reviewed.
2. Mark carried-forward actions as still open unless closure evidence exists.
3. Draft closure rows/updates only where the meeting source or project evidence proves closure.
4. Flag overdue actions and stale owners.
5. Escalate overdue critical actions where cost, programme, authority, safety or compliance is threatened.

Do not close an action because it was discussed. Closure needs evidence that the action was done or deliberately cancelled by the right owner/forum.

### Step 9 - Route Handoffs

The minutes are a hub. Route:

- confirmed decisions -> `decision-record-system.md`;
- open decisions -> decision request or park-for-decision queue;
- action rows -> `register-maintenance-system.md` or action register draft rows;
- RFIs/questions -> `rfi-management-system.md`;
- cost issue -> `cost-report-system.md` or `cost-plan-system.md`;
- programme issue -> `programme-system.md`;
- variation/EOT issue -> `variation-management-system.md`;
- payment claim issue -> `progress-claim-assessment-system.md`;
- authority issue -> `authority-approvals-system.md`;
- consultant issue -> `consultant-coordination-system.md`;
- design issue -> `design-review-evaluation-system.md`;
- risk issue -> `risk-register-system.md`;
- formal escalation -> `escalation-note-system.md`;
- handover/defect issue -> `handover-pc-system.md`.

### Step 10 - Draft the Minutes

Every output is a draft for review.

Minimum frontmatter:

```yaml
---
status: draft
author: agent
date: YYYY-MM-DD
meeting_date: YYYY-MM-DD
meeting_forum: ""
attendees: []
apologies: []
seed_consulted: []
evidence_refs: []
---
```

Recommended body:

1. Meeting status and limits.
2. Attendees and apologies.
3. Agenda.
4. Decisions made.
5. Actions.
6. Open decisions / decisions required.
7. RFIs and clarifications.
8. Discussion summary.
9. Escalation triggers and handoffs.
10. Prior action review.
11. Assumptions and gaps.

For owner-facing minutes, lead with what the owner needs to decide or do. For site or contractual minutes, keep actions, decisions and formal records prominent and cite source records where needed.

### Step 11 - Quality Check

Before returning, check:

- every action has owner, due date, status, source and next action;
- confirmed decisions are separated from discussion;
- open decisions are not recorded as made decisions;
- escalation triggers are surfaced;
- RFIs are routed rather than hidden in discussion;
- prior actions are not closed without evidence;
- owner/Principal directions are quoted where available;
- no contractual direction is issued without authority.

### Step 12 - Return Summary

Return:

- minutes draft path;
- action rows drafted;
- decision rows or decision requests drafted;
- RFIs or handoffs created;
- escalations surfaced;
- assumptions/gaps;
- tests or fixture checks run.

## Guardrails

- Do not bypass the three-overlay declaration gate.
- Do not use another project's evidence.
- Do not record discussion in place of a decision.
- Do not create vague actions without owner, due date and status.
- Do not close actions without evidence.
- Do not paraphrase owner/Principal directions where source wording exists.
- Do not issue contractual directions, approve variations, certify claims or approve design through minutes.
- Do not hide escalation triggers in general discussion.
- Do not update Excel registers without Excel-safe skills.
- Do not write to `project.db`.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/evidence-sweep.md` - active-project evidence sweep.
- `../atomic/markdown-draft-for-review.md` - draft minutes output discipline.
- `../atomic/register-row-draft.md` - action, decision, RFI, risk and escalation row drafting.
- `decision-record-system.md` - append-only decision records.
- `register-maintenance-system.md` - action/decision register hygiene and stale-row reporting.
- `rfi-management-system.md` - RFI intake, routing and response tracking.
- `escalation-note-system.md` - role-shaped escalation notes.
- `risk-register-system.md` - risk rows and risk commentary.
- `programme-system.md` - programme actions and critical-path impacts.
- `cost-report-system.md` - cost status and budget-pressure actions.
- `variation-management-system.md` - variation/EOT consequences.
- `consultant-coordination-system.md` - consultant deliverables and advice.
- `design-review-evaluation-system.md` - design decisions and design risks.
- `authority-approvals-system.md` - approval and condition actions.
- `../../00-doctrine/doctrine.md` - evidence, decision, register, escalation, voice and owner-communication discipline.

## Fixture Check

Use `../../99-docs/issues/sitewise-skills-framework-alignment/fixtures/meeting-minutes/bennett-budget-meeting-minutes-fixture-check.md` as the regression fixture. A passing review produces:

- minutes that separate discussion from owner decisions and open decisions;
- draft action rows with owner, due date and status;
- draft decision rows for confirmed directions only;
- escalation and handoff routing for budget pressure, procurement posture, programme gaps and consultant/design controls.
