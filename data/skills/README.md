# Skills

Reusable SiteWise workflows for residential project management.

`02-skills/` is the canonical workflow contract layer. The Clerk app implements these contracts; it is not a parallel source of truth for workflow behaviour.

## Path Mapping (standalone workspace → this repo)

Skill files were authored against the numbered standalone-workspace convention.
When a skill references one of those paths, translate it:

| Skill reference | In this repo |
| --- | --- |
| `00-doctrine/doctrine.md` | `docs/clerk-brief.md` (the SiteWise Doctrine) |
| `01-seed/` | `data/seed/` |
| `02-skills/` | `data/skills/` |
| `AGENTS.md` (workspace root) | Hosted product: the three-overlay declaration lives on the `projects` record (`archetype`, `user_role`, `state`), not a README frontmatter |
| `04-projects/<project>/` | Hosted product: Supabase Storage via `workspace_files` |
| `project.db` | Does not exist. The hosted substrate is Postgres (see Substrate Boundary below) |

## Status Vocabulary

Each indexed skill carries a STATUS:

- **implemented-in-clerk** — the contract's behaviour is live in the hosted product (the file remains the spec).
- **superseded-by-runtime** — a runtime mechanism now does this job; the file is design rationale.
- **standalone-era** — assumes the Markdown/Excel standalone substrate; not applicable to the hosted product.
- **future-hermes-workflow** — candidate for a Hermes-driven workflow; not yet implemented.

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

Markdown and Excel are the active register and tracker substrates in the standalone v1 convention. `project.db` never became real and is not a target. The hosted product's substrate is Postgres (Supabase): documents in `source_documents`/`workspace_files`, drafts in `draft_artifacts`, knowledge served through the platform-knowledge catalog.

## Index

### atomic/

| Skill | STATUS | Job |
| --- | --- | --- |
| `evidence-sweep.md` | superseded-by-runtime | Sweep the active project folder for relevant artefacts before drafting. Hosted: hybrid corpus retrieval + `search_documents`. |
| `seed-targeted-read.md` | superseded-by-runtime | Load only the seed guides that match the project overlays and task. Hosted: `backend/app/sitewise/knowledge_catalog.py` + the `list_platform_knowledge` / `read_platform_knowledge` MCP tools. |
| `markdown-draft-for-review.md` | implemented-in-clerk | Produce a draft markdown output with provenance and review status (hosted: `draft_artifacts`). |
| `register-row-draft.md` | future-hermes-workflow | Propose register rows for review before any controlled register update. |
| `excel-safe-edit.md` | standalone-era | Edit `.xlsx` files without breaking formulas, tables or validations. |
| `excel-verify.md` | standalone-era | Post-edit checklist for Excel work. |

### _shared/

| Skill | STATUS | Job |
| --- | --- | --- |
| `pm-contract.md` | implemented-in-clerk | Shared system-skill execution contract. Its disciplines (authority stack, seed_consulted audit, evidence labelling) are enforced in `backend/app/assistant/instructions.md` and the deterministic workflows. |

### systems/

| Skill | STATUS | Job |
| --- | --- | --- |
| `contract-setup-system.md` | implemented-in-clerk | Framework alias `commission-pmp`; commissioning, architect-PM PMP facet, contract setup and ready-to-start workflow (hosted: `backend/app/workflows/create_pmp.py`). |
| `cost-plan-system.md` | implemented-in-clerk | Framework alias `cost-plan`; cost plan preparation, review and workbook update (hosted: `backend/app/workflows/create_cost_plan.py`). |
| `document-intake-register-system.md` | implemented-in-clerk | Framework alias `document-intake-register`; canonical contract for Clerk Sort Files and document intake. |
| `cost-report-system.md` | future-hermes-workflow | Framework alias `cost-report`; recurring cost report, contingency, invoice, variation and budget-pressure reconciliation. |
| `decision-record-system.md` | future-hermes-workflow | Framework alias `decision-record`; append-only project decision register workflow. Earmarked as the CM-native memory design (decision register as project memory). |
| `escalation-note-system.md` | future-hermes-workflow | Framework alias `escalation-note`; early-warning note, role-shaped routing and recommended action workflow. |
| `handover-pc-system.md` | future-hermes-workflow | Framework alias `handover-dlp-plan`; handover, practical completion and DLP close-out. |
| `meeting-minutes-system.md` | future-hermes-workflow | Framework alias `meeting-minutes`; meeting records that separate discussion, decisions, actions and escalation handoffs. |
| `programme-system.md` | future-hermes-workflow | Framework alias `programme`; baseline, revised programme, milestone, lookahead and critical-path workflow. |
| `authority-approvals-system.md` | future-hermes-workflow | Framework alias `authority-approvals`; approval pathway, authority tracker, consent-condition register and approval handoffs. |
| `consultant-coordination-system.md` | future-hermes-workflow | Framework alias `consultant-coordination`; consultant appointments, responsibility matrix, deliverables, advice and design-question controls. |
| `design-review-evaluation-system.md` | future-hermes-workflow | Framework alias `design-review-evaluation`; design submissions reviewed against brief, budget, authority, compliance and responsibility boundaries. |
| `procurement-evaluation-system.md` | future-hermes-workflow | Framework alias `procurement-evaluation`; stage-aware procurement strategy, RFT, evaluation and recommendation workflow. |
| `project-report-system.md` | future-hermes-workflow | Framework alias `project-report`; recurring owner/internal reporting across time, cost, scope, quality, risk and source-control gaps. |
| `progress-claim-assessment-system.md` | future-hermes-workflow | Framework alias `payment-claim-assessment`; claim reconciliation and payment recommendation. |
| `risk-register-system.md` | future-hermes-workflow | First-class Tier 1 residential risk register workflow. |
| `register-maintenance-system.md` | future-hermes-workflow | Framework alias `register-maintenance`; general register hygiene, reconciliation and stale-row reporting. |
| `rfi-management-system.md` | future-hermes-workflow | Framework alias `rfi-management`; RFI intake, routing, response coordination, due-date tracking and impact handoffs. |
| `variation-management-system.md` | future-hermes-workflow | Framework alias `variation-eot-assessment`; variation and EOT evidence assessment. |

New gap workflows use `*-system.md` filenames and are sequenced by `../99-docs/issues/sitewise-skills-framework-alignment/`.

### reference/

| Skill | STATUS | Job |
| --- | --- | --- |
| `nsw-residential-cost-breakdown-reference.md` | implemented-in-clerk | Practice-level NSW residential cost taxonomy for cost planning and reporting. Runtime-required by the Create Cost Plan workflow (`backend/app/sitewise/cost_plan_sources.py`). |
