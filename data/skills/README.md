# Skills

Reusable SiteWise workflows for residential project management.

`02-skills/` is the canonical workflow contract layer. The Clerk app implements these contracts; it is not a parallel source of truth for workflow behaviour.

```text
02-skills/
  atomic/      # one-job mechanics used by systems
  systems/     # invokable workflow contracts
  _shared/     # non-invoked shared contracts
  reference/   # skill-adjacent reference material
```

## Split Rule

- **Atomic skill** - performs one operation. It does not call other skills internally. Examples: `evidence-sweep`, `register-row-draft`, `excel-safe-edit`.
- **System skill** - orchestrates a workflow by calling atomics in sequence, with review checkpoints and domain-specific rules. Examples: `cost-plan-system`, `risk-register-system`, `procurement-evaluation-system`.
- **Shared contract** - non-invoked inheritance material used by many skills. Current file: `_shared/pm-contract.md`.
- **Reference material** - governed support material that a workflow may load, but which is not a workflow. Current file: `reference/nsw-residential-cost-breakdown-reference.md`.

## Authoring Rule

Before creating a new skill:

1. Search `atomic/`, `systems/`, `_shared/` and `reference/` for existing coverage.
2. Put reusable one-job mechanics in `atomic/`.
3. Put framework catalogue workflows in `systems/` with `*-system.md` filenames.
4. Put shared non-invoked contracts in `_shared/`.
5. Put reference material in `reference/`.
6. Do not duplicate 60% or more of an existing skill; extend or parameterise the existing one.
7. Keep voice, evidence, register and seed discipline anchored in doctrine and `pm-contract`; do not make those rules separate skills.

## System Contract

Every system skill inherits `_shared/pm-contract.md` unless the skill file states a justified exception. The inherited sequence is:

1. Sec. 2 declaration gate at the system-skill boundary.
2. `seed-targeted-read` where seed consultation applies.
3. `evidence-sweep`.
4. Workflow-specific assessment.
5. `register-row-draft` and/or `markdown-draft-for-review`.
6. `excel-safe-edit` and `excel-verify` for Excel work.
7. Gaps, escalations and return summary.

## Skill File Format

Every skill file must state:

1. **Job** - what this skill does or orchestrates, in one sentence.
2. **When to use** - triggering conditions in the caller's terms.
3. **Caller passes / Inputs** - what must be supplied.
4. **Steps / Sequence** - numbered.
5. **Output location** - folder per `AGENTS.md` output rules.
6. **Rules / Must not do** - hard constraints.
7. **See also** - related skills, reference material and doctrine anchors.

## Substrate Boundary

Markdown and Excel are the active register and tracker substrates in v1. `project.db` remains a future migration target only; current skills and Clerk local-v1 workflows do not write to it.

## Index

### atomic/

- `evidence-sweep.md` - sweep the active project folder for relevant artefacts before drafting.
- `seed-targeted-read.md` - load only the seed guides that match the project overlays and task.
- `markdown-draft-for-review.md` - produce a draft markdown output with provenance and review status.
- `register-row-draft.md` - propose register rows for review before any controlled register update.
- `excel-safe-edit.md` - edit `.xlsx` files without breaking formulas, tables or validations.
- `excel-verify.md` - post-edit checklist for Excel work.

### _shared/

- `pm-contract.md` - shared system-skill execution contract.

### systems/

- `contract-setup-system.md` - framework alias `commission-pmp`; commissioning, architect-PM PMP facet, contract setup and ready-to-start workflow.
- `cost-report-system.md` - framework alias `cost-report`; recurring cost report, contingency, invoice, variation and budget-pressure reconciliation.
- `cost-plan-system.md` - framework alias `cost-plan`; cost plan preparation, review and workbook update.
- `decision-record-system.md` - framework alias `decision-record`; append-only project decision register workflow.
- `document-intake-register-system.md` - framework alias `document-intake-register`; canonical contract for Clerk Sort Files and document intake.
- `escalation-note-system.md` - framework alias `escalation-note`; early-warning note, role-shaped routing and recommended action workflow.
- `handover-pc-system.md` - framework alias `handover-dlp-plan`; handover, practical completion and DLP close-out.
- `meeting-minutes-system.md` - framework alias `meeting-minutes`; meeting records that separate discussion, decisions, actions and escalation handoffs.
- `programme-system.md` - framework alias `programme`; baseline, revised programme, milestone, lookahead and critical-path workflow.
- `authority-approvals-system.md` - framework alias `authority-approvals`; approval pathway, authority tracker, consent-condition register and approval handoffs.
- `consultant-coordination-system.md` - framework alias `consultant-coordination`; consultant appointments, responsibility matrix, deliverables, advice and design-question controls.
- `design-review-evaluation-system.md` - framework alias `design-review-evaluation`; design submissions reviewed against brief, budget, authority, compliance and responsibility boundaries.
- `procurement-evaluation-system.md` - framework alias `procurement-evaluation`; stage-aware procurement strategy, RFT, evaluation and recommendation workflow.
- `project-report-system.md` - framework alias `project-report`; recurring owner/internal reporting across time, cost, scope, quality, risk and source-control gaps.
- `progress-claim-assessment-system.md` - framework alias `payment-claim-assessment`; claim reconciliation and payment recommendation.
- `risk-register-system.md` - first-class Tier 1 residential risk register workflow.
- `register-maintenance-system.md` - framework alias `register-maintenance`; general register hygiene, reconciliation and stale-row reporting.
- `rfi-management-system.md` - framework alias `rfi-management`; RFI intake, routing, response coordination, due-date tracking and impact handoffs.
- `variation-management-system.md` - framework alias `variation-eot-assessment`; variation and EOT evidence assessment.

New gap workflows use `*-system.md` filenames and are sequenced by `../99-docs/issues/sitewise-skills-framework-alignment/`.

### reference/

- `nsw-residential-cost-breakdown-reference.md` - practice-level NSW residential cost taxonomy for cost planning and reporting.
