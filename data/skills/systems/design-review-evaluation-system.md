# System skill: design-review-evaluation-system

**Job:** Review SiteWise design submissions against the brief, budget, authority pathway, consultant responsibility and residential compliance constraints, then produce a design status summary, design-risk view and decision prompts for human review.

This system inherits `../_shared/pm-contract.md`. It is the canonical SiteWise workflow for alias `design-review-evaluation`.

## When to Use

Use this system when a SiteWise project needs to:

- review a design submission, drawing issue, sketch pack, consultant design input, or revised design set;
- compare design against the owner brief, cost plan, authority pathway, consultant advice, NCC/BCA Volume Two constraints, BASIX/NatHERS, bushfire, wastewater, accessibility or site constraints;
- summarise changes between design revisions;
- produce a design-risk view, owner decision pack, design phase-gate checklist, or tender/construction release review;
- separate design responsibility from project-management review responsibility before the design is used for authority, procurement, contract or construction decisions.

Do not use this system to create the design, certify compliance, approve construction, or replace the responsible architect/designer/consultant.

## Caller Passes

Required:

- Active project folder.
- Design input set or design register reference.
- Intended review purpose.

Optional:

- Mode: `submission-review`, `revision-comparison`, `phase-gate-check`, `design-risk-view`, `owner-decision-pack`, `tender-readiness-check`, `authority-alignment-check`, `budget-alignment-check`, `construction-release-check`.
- Specific drawing/document IDs.
- Known owner decisions, budget cap, cost plan version, authority pathway, consultant scopes or open RFIs.
- Output path override.

## Output Location

Use the smallest output that fits the review purpose:

| Output | Default path |
|---|---|
| Design review summary | `03-design/design-review-vNN.md` |
| Revision comparison | `03-design/revision-comparison-vNN.md` |
| Design-risk view | `03-design/design-risk-view-vNN.md` |
| Phase-gate design checklist | `03-design/design-phase-gate-checklist-vNN.md` |
| Tender readiness check | `05-procurement/design-tender-readiness-check-vNN.md` |
| Construction release check | `03-design/construction-release-check-vNN.md` |
| Owner design decision pack | `08-meetings-reporting/owner-design-decision-pack-vNN.md` |
| Design RFI or query register | `03-design/design-rfi-register.md` or `07-construction/08-rfi-notices/design-rfi-register.md` |

All markdown outputs use `../atomic/markdown-draft-for-review.md`. Register rows use `../atomic/register-row-draft.md`.

## Pre-flight

Before doing design review work:

1. Confirm the active project boundary from the project `README.md`.
2. Enforce the `AGENTS.md Sec. 2` three-overlay declaration gate. If `archetype`, `user_role`, or `state` is missing, blank, or `TBC`, stop and ask before continuing.
3. Read `00-doctrine/doctrine.md` for evidence, assumption, seed-consultation, voice and review discipline.
4. Read the project brief, latest design register or document intake register, current cost plan and current authority pathway note if they exist.
5. Confirm the review purpose and what the output will be used for.

## Workflow

### 1. Load Seeds Deliberately

Use `../atomic/seed-targeted-read.md`.

Minimum seed set when brief, budget, authority, compliance, procurement or construction release gates are live:

- Tier 2 archetype seed from `archetype:`.
- Tier 3 role overlay seed from `user_role:`.
- `setup-and-site-discovery.md` where site constraints affect design.
- `cost-management.md` where budget or value decisions are affected.
- `program-scheduling.md` where programme, approvals or long-lead design decisions are affected.
- `procurement-and-quoting.md` where the design will be priced, tendered or built.
- `sustainability-and-energy.md` where BASIX, NatHERS, glazing, ventilation, insulation or energy compliance is affected.
- `ncc-reference.md` where NCC/BCA Volume Two, waterproofing, fire, access, structural adequacy or class constraints are affected.
- `contract-admin.md` where design changes may become variations, EOT issues, notices or release-for-construction risk.
- Technical or trade seeds where the review touches bushfire, wastewater, structure, cladding, roofing, windows, wet areas, services, landscape, pool, joinery or other specialist scope.

Record every seed consulted in `seed_consulted:`.

For non-NSW states, apply available inline state callouts in the loaded seeds. If no state guidance exists for a material issue, flag the gap and ask for project-lead input rather than assuming NSW.

### 2. Build the Evidence Set

Read only active-project evidence. Prefer current source documents and current registers over summaries.

Minimum evidence sweep:

- `00-brief-pmp/` for owner brief, PM scope, budget, programme, values, exclusions and decision history.
- `01-cost/` for cost plan, QS notes, budget tracker and cost-risk items.
- `02-consultant/` for scopes, advice, reports, gaps, declined scopes and consultant responsibility limits.
- `03-design/` for drawings, specifications, sketches, revision history and design registers.
- `04-planning-and-authorities/` for authority pathway, DA/CDC status, certificates, conditions and approvals constraints.
- `05-procurement/` if the design is being tendered or quoted.
- `07-construction/` if design information is being used on site.
- `08-meetings-reporting/` for owner decisions, meeting minutes and stakeholder commitments.

If an important source is missing, record the absence as a gap. Do not infer the missing content from a drawing title or file name.

### 3. Resolve Design Baseline and Revision Status

Create a design-source table before evaluating content.

For each source, record:

- document number;
- title;
- author or discipline;
- revision;
- issue date;
- issue purpose;
- superseded/current/unclear status;
- related consultant or authority source;
- review use allowed now.

Do not treat drawings as self-explanatory. A drawing note, symbol, hatch, revision cloud or schedule entry is evidence only after it is read against the document title block, revision status, issue purpose, related reports and the project brief.

If current design material conflicts with superseded material, use the current material and record the superseded material as a warning only. If no current material exists for a material design area, record a design information gap.

### 4. Compare Against Brief and Scope

Use the brief and decision history as the baseline, then test whether the design:

- delivers the required spaces, uses and functional priorities;
- respects explicit owner priorities, exclusions and decision records;
- adds scope that was not briefed or approved;
- omits or weakens a brief item;
- converts a preference into a cost/compliance obligation without a recorded decision;
- creates a decision for the owner, architect, PM, certifier, builder or consultant.

Separate:

- `matches brief`;
- `exceeds brief`;
- `under-resolves brief`;
- `requires owner decision`;
- `requires consultant/design-team action`;
- `requires PM coordination`.

### 5. Compare Against Budget and Cost Plan

Read the latest cost plan, QS note, budget tracker and procurement evidence.

Identify design features that may affect:

- total construction cost;
- consultant fees;
- authority fees and levies;
- provisional sums and exclusions;
- programme preliminaries;
- long-lead procurement;
- buildability and staging;
- maintenance or lifecycle cost;
- value-management options.

If the design materially affects the budget or a cost plan is stale/missing, route a follow-up to `cost-plan-system.md`. Do not declare a design budget-aligned without cost evidence.

### 6. Compare Against Authority and Compliance Pathway

Read the current authority pathway note, approvals register, certifier advice and relevant consultant reports.

Check whether the design:

- fits the nominated approval pathway;
- creates DA/CDC/planning pathway risk;
- creates BASIX/NatHERS, NCC/BCA Volume Two, bushfire, wastewater, stormwater, tree, heritage, easement, boundary, fire separation or pool compliance issues;
- depends on a certificate, consultant scope, report or approval that has not been obtained;
- introduces a construction-release issue that must be resolved before tender, contract, CC, PCA or site work.

If the design affects approval strategy or approval evidence, route the item to `authority-approvals-system.md`. If consultant scope or sequencing is the blocker, route it to `consultant-coordination-system.md`.

### 7. Respect Design Responsibility Boundaries

Classify each finding by responsibility:

- owner decision;
- architect/designer action;
- specialist consultant action;
- certifier/PCA advice;
- builder/buildability input;
- PM coordination;
- authority determination;
- no current owner/PM action.

Use PM language: "review finding", "coordination issue", "decision required", "risk to resolve". Do not say the agent has approved, certified, designed, engineered or warranted the design.

Where a design question is professional design responsibility, ask for the responsible consultant or designer to respond. Where the PM can coordinate, list the next PM action.

### 8. Summarise Revision Changes

For each revised design set, summarise:

- what changed from the previous revision;
- what the change affects: brief, budget, authority, compliance, programme, procurement, constructability, owner decision or consultant coordination;
- whether the change closes, worsens or creates a design risk;
- whether it needs a decision record, RFI, consultant response, cost update or authority update.

If the previous revision is unavailable, state that the comparison is partial.

### 9. Produce a Design-Risk View

Use this schema unless the project already has a design-risk register:

| Field | Purpose |
|---|---|
| `risk_id` | `DR-<seq>` |
| `source_ref` | Drawing/report/register evidence |
| `design_area` | Site, planning, structure, envelope, wet areas, services, pool, landscape, interiors, authority, cost, programme |
| `finding` | Concise evidence-based issue |
| `impact` | Brief, budget, authority, compliance, programme, procurement, construction or owner decision |
| `responsible_party` | Owner, architect, consultant, certifier, builder, PM, authority |
| `next_action` | Specific action |
| `decision_needed` | Yes/no and by whom |
| `status` | `draft`, `open`, `watch`, `resolved`, `superseded` |
| `seed_consulted` | Seed list |
| `evidence_refs` | Evidence list |

### 10. Draft Decision Prompts

Owner and project-lead prompts must be answerable and consequential.

Use this pattern:

- `Decision:` the choice to make.
- `Why now:` the gate or risk created by the design.
- `Options:` usually 2-4 options, including defer/drop/phase where realistic.
- `PM recommendation:` if evidence supports one, otherwise state what evidence is missing.
- `Effect of no decision:` the practical project consequence.

Convert high-impact decisions to `decision-record-system.md`.

### 11. Shape by Role and Archetype

Use the role overlay to decide tone and emphasis:

- Owner-builder: plain-language explanation, decision clarity and risk guardrails.
- Architect-PM: design responsibility separation, consultant coordination, authority/cost/programme impacts and owner instructions.
- Builder or D&C: buildability, information completeness, tender/contract/construction release constraints and design liability boundaries.

Use the archetype seed to test typical risks:

- New dwelling: siting, envelope, BASIX/NatHERS, NCC, bushfire/flood/wastewater, budget, pool/landscape, services and approvals.
- Renovation: existing conditions, latent defects, waterproofing, structure, heritage, staging and occupant disruption.
- Multi-dwelling: planning yield, fire/acoustic/access, strata/services, staging, authority and procurement complexity.
- Ancillary: interface with existing dwelling, setbacks, services, planning and proportionality.
- Small-commercial: tenancy, egress, accessibility, fire safety, fitout approvals and operational constraints.

### 12. Route Handoffs

Create follow-up actions, not silent assumptions:

- Decision needed -> `decision-record-system.md`.
- Register row needed -> `register-maintenance-system.md` or `../atomic/register-row-draft.md`.
- Authority pathway issue -> `authority-approvals-system.md`.
- Consultant scope/advice gap -> `consultant-coordination-system.md`.
- Budget/cost impact -> `cost-plan-system.md`.
- Programme impact -> `programme-system.md`.
- Formal escalation -> `escalation-note-system.md`.
- RFI or design query -> `rfi-management-system.md`.
- Procurement effect -> relevant procurement/tender workflow.

### 13. Draft the Output

Every output is a draft for review.

Minimum markdown frontmatter:

```yaml
---
status: draft
author: agent
date: YYYY-MM-DD
seed_consulted: []
evidence_refs: []
---
```

Minimum body:

1. Review purpose and limits.
2. Evidence set and revision baseline.
3. Executive design status.
4. Brief alignment.
5. Budget alignment.
6. Authority/compliance alignment.
7. Revision changes.
8. Design-risk view.
9. Decisions required.
10. Handoffs and next actions.
11. Assumptions and gaps.

If the output is owner-facing, use stakeholder register and plain English. If it is contractual, procurement, authority or construction-release related, use contractual register and cite clauses/conditions where available.

### 14. Maintain Registers Safely

If creating or updating a design-risk register, decision register, authority register or consultant tracker:

- use `../atomic/register-row-draft.md`;
- preserve existing IDs, statuses and provenance;
- add rows as draft unless a human has reviewed them;
- do not overwrite Excel registers without the Excel-safe skills.

### 15. Escalate Gaps

Escalate when:

- a design is about to be used for authority, tender, contract or construction without current revision evidence;
- the design exceeds budget or relies on unfunded scope;
- an owner decision blocks a compliance, cost or programme gate;
- consultant design responsibility is unclear;
- authority pathway risk may invalidate the next phase;
- the design depends on neighbour land, easements, certificates, owner consents, or unavailable consultant scopes;
- superseded drawings are being used as current.

Use `escalation-note-system.md` for formal cross-control warnings.

### 16. Return Summary

Return:

- output paths created or updated;
- design status in one sentence;
- top risks and decisions;
- handoffs created;
- assumptions/gaps;
- tests or fixture checks run.

## Guardrails

- Do not bypass the three-overlay declaration gate.
- Do not use another project's evidence.
- Do not approve, certify, engineer, design or warrant the design.
- Do not treat drawings as self-explanatory.
- Do not call the design budget-aligned without current cost evidence.
- Do not call the design approval-ready without authority evidence.
- Do not rely on superseded drawings except to explain history or flag risk.
- Do not convert owner preferences into scope without a decision record.
- Do not hide design responsibility inside PM wording.
- Do not update Excel registers without Excel-safe skills.
- Do not write to `project.db`.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/seed-targeted-read.md` - targeted seed loading.
- `../atomic/evidence-sweep.md` - active-project evidence sweep.
- `../atomic/markdown-draft-for-review.md` - draft markdown output discipline.
- `../atomic/register-row-draft.md` - design-risk, decision, authority or consultant register row drafting.
- `decision-record-system.md` - owner/project-lead design decisions.
- `authority-approvals-system.md` - approval pathway and consent-condition impacts.
- `consultant-coordination-system.md` - consultant scope, deliverable and advice gaps.
- `cost-plan-system.md` - budget impact and value-management follow-up.
- `programme-system.md` - programme impact and critical-path follow-up.
- `rfi-management-system.md` - design RFI and formal RFI intake, routing and response tracking.
- `escalation-note-system.md` - formal cross-control warnings.
- `../../00-doctrine/doctrine.md` - evidence, seed, register, decision, voice and escalation discipline.

## Fixture Check

Use `../../99-docs/issues/sitewise-skills-framework-alignment/fixtures/design-review-evaluation/bennett-da-rev-b-design-review-fixture.md` as the regression fixture. A passing review produces:

- a design-source baseline that distinguishes current Rev B drawings from superseded Rev A drawings;
- a design-risk view covering brief, budget, authority, consultant and compliance impacts;
- owner/project-lead decision prompts;
- explicit responsibility separation between architect/designer, specialist consultants, certifier, PM and owner.
